"""
live_scorer.py — Fetches real commodity signals from free public APIs.

Data sources:
  - yfinance ETF/equity proxies — weekly price delta for each mineral
  - Google News RSS — export restriction headline count (7-day window)
  - Static HHI from USGS Mineral Commodity Summaries 2025
  - Semi-static trade routes from USGS/UN Comtrade

No API keys required.
"""

from __future__ import annotations

import json
import logging
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
import yfinance as yf

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
SCORES_PREV_PATH = DATA_DIR / "scores_prev.json"

# ── Price proxies ─────────────────────────────────────────────────────────────
# yfinance tickers used as weekly price direction proxies.
# Multiple tickers per mineral → averaged to reduce single-stock noise.
PRICE_TICKERS = {
    "Gallium": ["REMX", "MP"],      # VanEck Rare Earth ETF + MP Materials
    "Cobalt":  ["GLNCY"],           # Glencore ADR (world's largest cobalt producer)
    "Lithium": ["LIT", "SQM", "ALB"],  # Global X Lithium ETF + SQM + Albemarle
}

# Reference spot prices in $/tonne (USGS 2025 / LME Q1 2026 averages)
# Updated weekly via proxy delta below
BASE_PRICES = {
    "Gallium": 418_000,
    "Cobalt":   33_800,
    "Lithium":  12_400,
}

# ── Trade concentration (HHI, 0–10000) ───────────────────────────────────────
# Source: USGS Mineral Commodity Summaries 2025. Updated yearly.
HHI = {
    "Gallium": 8500,  # China >85% of world mine production
    "Cobalt":  4900,  # DRC ~73%
    "Lithium": 2500,  # Australia ~47%, Chile ~27%
}

# ── Trade routes (semi-static) ────────────────────────────────────────────────
ROUTES = {
    "Gallium": [
        {"origin": "China",     "destination": "EU",  "mode": "air+sea", "status": "restricted", "volume_pct": 82},
        {"origin": "China",     "destination": "USA", "mode": "sea",     "status": "restricted", "volume_pct": 11},
    ],
    "Cobalt": [
        {"origin": "DRC",       "destination": "China",   "mode": "rail+sea", "status": "normal", "volume_pct": 68},
        {"origin": "DRC",       "destination": "Belgium", "mode": "sea",      "status": "normal", "volume_pct": 14},
    ],
    "Lithium": [
        {"origin": "Chile",     "destination": "Japan",       "mode": "sea", "status": "normal", "volume_pct": 31},
        {"origin": "Australia", "destination": "China",       "mode": "sea", "status": "normal", "volume_pct": 45},
    ],
}

# ── Structural fallback factors ───────────────────────────────────────────────
STRUCTURAL_FACTORS = {
    "Gallium": [
        {"factor": "China export licensing regime", "weight": 0.60,
         "description": "China controls >85% of global gallium output; ongoing MOFCOM export licensing since Aug 2023"},
        {"factor": "No viable GaN substitute", "weight": 0.25,
         "description": "Gallium nitride is critical for 5G RF chips, EV chargers and radar with no short-run substitute"},
        {"factor": "Limited ex-China stockpiles", "weight": 0.15,
         "description": "EU strategic reserve estimated at ~4 months coverage; US NDS assessment pending"},
    ],
    "Cobalt": [
        {"factor": "DRC supply concentration", "weight": 0.55,
         "description": "DRC produces ~73% of global cobalt; artisanal mining instability creates persistent export risk"},
        {"factor": "EV battery demand growth", "weight": 0.30,
         "description": "IEA revised 2026 EV adoption up 9%; sustained demand growth with limited cobalt substitution in high-energy cells"},
        {"factor": "Glencore Mutanda operations", "weight": 0.15,
         "description": "Mutanda is the world's largest cobalt mine; output guidance changes materially move global supply"},
    ],
    "Lithium": [
        {"factor": "Australia-Chile production duopoly", "weight": 0.45,
         "description": "Australia (~47%) and Chile (~27%) dominate supply; concentration in two regulatory jurisdictions"},
        {"factor": "Chinese refining concentration", "weight": 0.35,
         "description": "China refines ~60% of global lithium carbonate; trade tensions create processing bottleneck risk"},
        {"factor": "Gigafactory demand acceleration", "weight": 0.20,
         "description": "Accelerating EV and grid-storage deployments driving multi-year demand growth"},
    ],
}


# ── Price fetch ───────────────────────────────────────────────────────────────

def _price_delta(mineral: str) -> tuple[float, float]:
    """Returns (price_usd_per_tonne, price_delta_pct) using yfinance proxy tickers."""
    tickers = PRICE_TICKERS[mineral]
    deltas: list[float] = []
    for sym in tickers:
        try:
            hist = yf.Ticker(sym).history(period="2wk", auto_adjust=True)
            if hist.empty or len(hist) < 2:
                continue
            cur  = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[0])
            if prev:
                deltas.append((cur - prev) / prev * 100)
        except Exception as e:
            log.warning(f"yfinance {sym}: {e}")
    avg_delta = round(sum(deltas) / len(deltas), 1) if deltas else 0.0
    estimated_price = round(BASE_PRICES[mineral] * (1 + avg_delta / 100))
    return estimated_price, avg_delta


# ── News fetch ────────────────────────────────────────────────────────────────

def _news(mineral: str, days: int = 7) -> tuple[int, list[dict]]:
    """
    Returns (article_count, top_factors) from Google News RSS.
    Falls back to structural factors if no recent articles found.
    """
    query = f"{mineral} export controls OR supply disruption OR sanctions OR price spike"
    url = (
        f"https://news.google.com/rss/search"
        f"?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles: list[tuple[datetime, str]] = []

    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "SupplyWatch/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            pub_raw = item.findtext("pubDate", "")
            try:
                pub_dt = parsedate_to_datetime(pub_raw)
                if pub_dt > cutoff and title:
                    articles.append((pub_dt, title))
            except Exception:
                pass
    except Exception as e:
        log.warning(f"Google News RSS error for {mineral}: {e}")

    articles.sort(key=lambda x: x[0], reverse=True)
    count = len(articles)

    if articles:
        weights = [0.50, 0.30, 0.20]
        top_factors = [
            {
                "factor": title[:80],
                "weight": weights[i] if i < 3 else 0.10,
                "description": f"Google News, {pub_dt.strftime('%b %d %Y')}",
            }
            for i, (pub_dt, title) in enumerate(articles[:3])
        ]
        # Pad with structural factors if fewer than 3 news items
        structural = STRUCTURAL_FACTORS[mineral]
        while len(top_factors) < 3:
            idx = len(top_factors)
            top_factors.append({
                **structural[idx % len(structural)],
                "weight": 0.15,
            })
    else:
        top_factors = STRUCTURAL_FACTORS[mineral]

    return count, top_factors


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score(price_delta_pct: float, news_count: int, hhi: float) -> int:
    price_s  = min(100, max(0, abs(price_delta_pct)))
    export_s = min(100, news_count * 20)
    trade_s  = min(100, hhi / 100)
    return int(price_s * 0.30 + export_s * 0.40 + trade_s * 0.30)


# ── Score history ─────────────────────────────────────────────────────────────

def _load_prev() -> dict[str, int]:
    if SCORES_PREV_PATH.exists():
        return json.loads(SCORES_PREV_PATH.read_text())
    return {}


def _save_current(scores: dict[str, int]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SCORES_PREV_PATH.write_text(json.dumps(scores, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

def build_scorer_output(minerals: list[str] | None = None) -> list[dict]:
    """
    Fetch live signals and return scorer output JSON list,
    matching the format expected by reports/prompt_template.py.
    """
    if minerals is None:
        minerals = list(PRICE_TICKERS.keys())

    today = date.today()
    prev_scores = _load_prev()
    current_scores: dict[str, int] = {}
    output: list[dict] = []

    for name in minerals:
        log.info(f"[live_scorer] {name}: fetching price…")
        price_usd_t, price_delta_pct = _price_delta(name)
        time.sleep(1)

        log.info(f"[live_scorer] {name}: fetching news…")
        news_count, top_factors = _news(name)
        time.sleep(1)

        hhi = HHI[name]
        score = _score(price_delta_pct, news_count, hhi)
        current_scores[name] = score

        prev = prev_scores.get(name, score)
        delta = score - prev
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"

        sources = ["yfinance proxy", "Google News", "USGS HHI"]
        if name in ("Cobalt", "Lithium"):
            sources.insert(0, "LME proxy")

        output.append({
            "mineral": name,
            "iso_code": {"Gallium": "Ga", "Cobalt": "Co", "Lithium": "Li"}.get(name, name[:2]),
            "score": score,
            "score_delta": delta,
            "score_direction": direction,
            "week_ending": today.isoformat(),
            "top_factors": top_factors,
            "affected_trade_routes": ROUTES[name],
            "price_usd_per_tonne": price_usd_t,
            "price_delta_pct": price_delta_pct,
            "data_sources": sources,
        })
        log.info(f"[live_scorer] {name}: score={score} price_delta={price_delta_pct:+.1f}% news={news_count}")

    _save_current(current_scores)
    return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data = build_scorer_output()
    print(json.dumps(data, indent=2))
