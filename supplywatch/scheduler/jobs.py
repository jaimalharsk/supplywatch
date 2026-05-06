from collections import defaultdict
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alerts.dispatcher import AlertDispatcher
from core.database import AlertHistory, AlertSubscription, AsyncSessionLocal, DisruptionScore, Material, RawSignal
from ingest.comtrade import ComtradeIngestor
from ingest.sanctions import SanctionsIngestor
from ingest.usgs import USGSIngestor
from signals.models import MaterialSignal
from signals.scorer import DisruptionScorer


async def run_pipeline(db: AsyncSession | None = None):
    owns_session = db is None
    if owns_session:
        async with AsyncSessionLocal() as owned_db:
            return await run_pipeline(owned_db)

    materials = (await db.execute(select(Material))).scalars().all()
    dispatcher = AlertDispatcher()
    for material in materials:
        collected: list[MaterialSignal] = []
        for cls in (USGSIngestor, ComtradeIngestor, SanctionsIngestor):
            ingestor = cls(material.name)
            try:
                raw = await ingestor.fetch()
                db.add(RawSignal(material_id=material.id, source=ingestor.source_name, raw_data=raw))
                collected.append(await ingestor.normalize(raw))
            except Exception as exc:
                print(f"[warn] {ingestor.source_name} failed for {material.name}: {exc}")
        score, factors = DisruptionScorer.score(collected)
        db.add(DisruptionScore(material_id=material.id, score=score, factors=factors))
        subs = (
            await db.execute(
                select(AlertSubscription).where(
                    AlertSubscription.material_id == material.id,
                    AlertSubscription.threshold <= score,
                )
            )
        ).scalars().all()
        for sub in subs:
            msg = await dispatcher.dispatch(sub, score)
            db.add(AlertHistory(subscription_id=sub.id, score_at_trigger=score, message=msg))
    await db.commit()


async def run_pipeline_once() -> None:
    """Convenience wrapper for isolated smoke testing of the scheduler pipeline."""
    await run_pipeline()


async def generate_digest(db: AsyncSession, api_key_id: int):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        await db.execute(
            select(DisruptionScore, Material)
            .join(Material, DisruptionScore.material_id == Material.id)
            .where(DisruptionScore.computed_at >= cutoff)
            .order_by(DisruptionScore.computed_at)
        )
    ).all()
    by_mat = defaultdict(list)
    for score, material in rows:
        by_mat[material.name].append(score.score)
    deltas = sorted(
        [(name, vals[-1] - vals[0]) for name, vals in by_mat.items() if len(vals) > 1],
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:3]
    text = "Weekly SupplyWatch Digest\n" + "\n".join([f"{name}: delta {delta}" for name, delta in deltas])
    html = "<h1>Weekly SupplyWatch Digest</h1>" + "".join([f"<p>{name}: delta {delta}</p>" for name, delta in deltas])
    return {"api_key_id": api_key_id, "text": text, "html": html}


def build_scheduler(session_factory):
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def _job():
        async with session_factory() as db:
            await run_pipeline(db)

    async def _digest_job():
        async with session_factory() as db:
            print(await generate_digest(db, 1))

    scheduler.add_job(_job, "interval", hours=6)
    scheduler.add_job(_digest_job, "cron", day_of_week="mon", hour=8, minute=0)
    return scheduler
