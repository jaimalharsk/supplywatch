"""
Orchestrates the weekly SupplyWatch posting pipeline.

Run manually:
    python -m pipeline.scheduler                  # full run
    python -m pipeline.scheduler --dry-run        # preview posts, no API calls
    python -m pipeline.scheduler --substack-only  # skip Reddit
    python -m pipeline.scheduler --reddit-only    # skip Substack

Add to crontab (every Monday 9am):
    0 9 * * 1 cd /home/malhar/cli/supplywatch && python -m pipeline.scheduler >> logs/pipeline.log 2>&1
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.teaser import reddit_title, reddit_body, substack_title

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

REPORTS_DIR = Path(__file__).parent.parent / "reports" / "output"
LOGS_DIR = Path(__file__).parent.parent / "logs"


def latest_report() -> tuple[str, str]:
    """Returns (markdown_text, date_str) for the most recent report."""
    reports = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    if not reports:
        raise FileNotFoundError(f"No reports in {REPORTS_DIR} — run the generator first")
    path = reports[0]
    return path.read_text(), path.stem


def run(dry_run=False, substack_only=False, reddit_only=False):
    LOGS_DIR.mkdir(exist_ok=True)
    md, report_date = latest_report()
    log.info(f"Report: {report_date}")

    substack_url = ""

    # ── Substack ──────────────────────────────────────────────────────────────
    if not reddit_only:
        log.info(f"\n=== Substack ===\nTitle: {substack_title(md, report_date)}")
        if dry_run:
            log.info("(dry run — skipping)")
        else:
            try:
                from pipeline.substack import SubstackPoster
                result = SubstackPoster().post(md, report_date)
                substack_url = result["url"]
                log.info(f"Substack posted: {substack_url}")
            except Exception as e:
                log.error(f"Substack failed: {e}")

    # ── Reddit ────────────────────────────────────────────────────────────────
    if not substack_only:
        preview_title = reddit_title(md, report_date)
        preview_body = reddit_body(md, report_date, substack_url)
        log.info(f"\n=== Reddit ===\nTitle: {preview_title}")
        log.info(f"Body preview (first 300 chars):\n{preview_body[:300]}…")
        if dry_run:
            log.info("(dry run — skipping)")
        else:
            try:
                from pipeline.reddit import RedditPoster
                results = RedditPoster().post(md, report_date, substack_url=substack_url)
                for r in results:
                    if r["error"]:
                        log.error(f"r/{r['subreddit']}: {r['error']}")
                    else:
                        log.info(f"r/{r['subreddit']}: {r['url']}")
            except Exception as e:
                log.error(f"Reddit failed: {e}")

    log.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    parser.add_argument("--substack-only", action="store_true")
    parser.add_argument("--reddit-only", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run, substack_only=args.substack_only, reddit_only=args.reddit_only)
