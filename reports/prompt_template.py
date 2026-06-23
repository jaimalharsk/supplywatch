"""
Builds the system + user prompt for SupplyWatch weekly briefs.

The scorer output schema (per mineral):
  mineral, iso_code, score (0-100), score_delta, score_direction,
  week_ending, top_factors [{factor, weight, description}],
  affected_trade_routes [{origin, destination, mode, status, volume_pct}],
  price_usd_per_tonne, price_delta_pct, data_sources
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any


SYSTEM_PROMPT = """\
You are a senior analyst at a commodity risk advisory firm. \
Your readers are procurement managers at small and mid-size manufacturing \
and electronics companies — they are not commodity traders. \
They need to know what changed, why it matters for their purchasing decisions, \
and what to do about it. Write in plain, direct English. \
No hedging phrases like "it may be worth considering." \
Be specific: name the mines, the countries, the companies, the volumes. \
Output exactly the four sections below, in Markdown, with no preamble."""


def _risk_label(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "ELEVATED"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def _direction_arrow(direction: str, delta: int) -> str:
    arrow = "▲" if direction == "up" else "▼" if direction == "down" else "→"
    return f"{arrow}{abs(delta)}"


def _format_mineral_block(m: dict[str, Any]) -> str:
    label = _risk_label(m["score"])
    arrow = _direction_arrow(m["score_direction"], m["score_delta"])
    price_direction = "up" if m["price_delta_pct"] > 0 else "down"

    factors = "\n".join(
        f"  - {f['factor']} ({f['weight']:.0%} weight): {f['description']}"
        for f in m["top_factors"]
    )

    routes = ", ".join(
        f"{r['origin']}→{r['destination']} ({r['mode']}, {r['volume_pct']}% of volume, status: {r['status']})"
        for r in m["affected_trade_routes"]
    )

    sources = ", ".join(m["data_sources"])

    return f"""\
### {m['mineral']} ({m['iso_code']})
Risk score: {m['score']}/100 [{label}] {arrow} this week
Spot price: ${m['price_usd_per_tonne']:,}/t ({price_direction} {abs(m['price_delta_pct'])}% WoW)

Top contributing factors:
{factors}

Affected trade routes: {routes}
Data sources: {sources}
"""


def build_user_prompt(minerals: list[dict[str, Any]], report_date: date | None = None) -> str:
    report_date = report_date or date.today()
    week_str = report_date.strftime("%B %d, %Y")

    # Sort: highest score first — lead with the most urgent mineral
    sorted_minerals = sorted(minerals, key=lambda m: m["score"], reverse=True)

    mineral_blocks = "\n".join(_format_mineral_block(m) for m in sorted_minerals)

    critical = [m["mineral"] for m in sorted_minerals if m["score"] >= 80]
    elevated = [m["mineral"] for m in sorted_minerals if 60 <= m["score"] < 80]

    headline_context = ""
    if critical:
        headline_context += f"Critical-level minerals this week: {', '.join(critical)}. "
    if elevated:
        headline_context += f"Elevated-level minerals: {', '.join(elevated)}."

    return f"""\
Write the SupplyWatch Weekly Disruption Brief for the week ending {week_str}.

{headline_context}

Below is the structured scorer output for each tracked mineral. \
Use this data as your primary source — do not invent facts. \
Where the data is ambiguous, say so briefly.

---
{mineral_blocks}
---

Output format — write exactly these four Markdown sections:

## Executive Summary
Two to three sentences. Name the single most urgent finding. \
State the overall risk posture for the week.

## What Moved
One subsection per mineral with a score ≥ 40 or a score_delta ≥ 10 (absolute). \
For each: one paragraph explaining what changed and the primary cause. \
Be specific — name entities, not just categories.

## Risk Outlook
A forward-looking paragraph (3–5 sentences) covering the 2–4 week horizon. \
Note any scheduled events (regulatory decisions, earnings, trade deadlines) \
that could shift scores materially.

## Recommended Actions
A numbered list of 3–5 concrete steps a procurement manager can take this week. \
Each item should be actionable in under 1 business day. \
Examples: "Request spot quotes from non-Chinese gallium refiners (Recylex DE, \
Neo Performance CA)." Not: "Consider diversifying your supply chain."
"""


def build_prompt_pair(
    minerals: list[dict[str, Any]], report_date: date | None = None
) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) ready to pass to the Anthropic SDK."""
    return SYSTEM_PROMPT, build_user_prompt(minerals, report_date)
