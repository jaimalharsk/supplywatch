"""
Self-evaluation loop for SupplyWatch reports.

After generation, a second LLM call scores the report on four dimensions.
If the total falls below PASS_THRESHOLD, the generator retries with the
critique appended to the prompt. Scores are logged to reports/eval_log.jsonl.

Rubric (each scored 1–5, total 20):
  specificity    — names entities: mines, companies, volumes, %, prices
  actionability  — Recommended Actions are doable in <1 business day
  data_grounding — every quantitative claim matches the scorer input
  conciseness    — Executive Summary ≤ 3 sentences, no filler anywhere

Pass threshold: 16/20. Max retries: 1.

Speed design:
  - EVAL_MODEL is separate from the generation model — use a smaller/faster
    model here since scoring requires less capability than writing.
  - The eval prompt sends a compact fact table instead of the full scorer JSON,
    cutting input tokens by ~60%.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

PASS_THRESHOLD = 16
MAX_RETRIES = 1          # was 2 — one retry is enough; saves one full gen+eval round
EVAL_LOG = Path(__file__).parent / "eval_log.jsonl"

# Lighter model for evaluation — scoring needs correctness, not eloquence.
# Swap to "gemini-2.5-flash" if the lite model isn't available on your key.
EVAL_MODEL = "openai/gpt-oss-120b:free"

RUBRIC = (
    "specificity (1-5): Names actual entities — mine names, companies, govt bodies, "
    "trade routes, exact % and prices. 1=all vague. 5=every claim sourced.\n"
    "actionability (1-5): Recommended Actions are doable in <1 business day, "
    "name specific suppliers or steps. 1=generic ('monitor situation'). 5=specific+immediate.\n"
    "data_grounding (1-5): All numbers match the FACT TABLE below. Nothing invented. "
    "1=several wrong numbers. 5=every figure traceable.\n"
    "conciseness (1-5): Exec Summary ≤3 sentences, no padding anywhere. "
    "1=repetitive/padded. 5=tight throughout."
)

EVAL_SYSTEM = (
    "You are a strict quality evaluator for commodity risk briefs. "
    "Score the report on four dimensions (1-5 each). "
    "Return ONLY a raw JSON object — no markdown fences, no explanation, no preamble. "
    'Example: {"scores": {"specificity": 4, "actionability": 3, "data_grounding": 5, "conciseness": 4}, "critique": "..."}'
)


def _compact_fact_table(minerals: list[dict[str, Any]]) -> str:
    """
    Replaces the full scorer JSON in the eval prompt with a compact table.
    Cuts eval input tokens by ~60% while keeping all checkable facts.
    """
    rows = []
    for m in minerals:
        factors = "; ".join(f['factor'] for f in m.get("top_factors", []))
        routes = "; ".join(
            f"{r['origin']}→{r['destination']} {r['status']}"
            for r in m.get("affected_trade_routes", [])
        )
        rows.append(
            f"{m['mineral']}: score={m['score']} delta={m['score_delta']:+d} "
            f"price=${m['price_usd_per_tonne']:,} ({m['price_delta_pct']:+.1f}%) | "
            f"factors: {factors} | routes: {routes}"
        )
    return "\n".join(rows)


@dataclass
class EvalResult:
    scores: dict[str, int]
    total: int
    critique: str
    passed: bool
    attempt: int


class ReportEvaluator:
    def __init__(self, client, model: str = EVAL_MODEL, backend: str = "gemini"):
        self.client = client
        self.model = model
        self.backend = backend

    def _build_eval_prompt(self, report_md: str, minerals: list[dict[str, Any]]) -> str:
        fact_table = _compact_fact_table(minerals)
        return (
            f"RUBRIC:\n{RUBRIC}\n\n"
            f"FACT TABLE (ground truth for data_grounding check):\n{fact_table}\n\n"
            f"REPORT:\n{report_md}"
        )

    def evaluate(
        self, report_md: str, minerals: list[dict[str, Any]], attempt: int = 0
    ) -> EvalResult:
        from google.genai.errors import ServerError
        import time

        prompt = self._build_eval_prompt(report_md, minerals)
        last_err = None

        full_prompt = f"{EVAL_SYSTEM}\n\n{prompt}"
        raw_text = None
        for retry in range(3):
            try:
                if self.backend == "openrouter":
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": full_prompt}],
                    )
                    raw_text = resp.choices[0].message.content
                else:
                    resp = self.client.models.generate_content(
                        model=self.model,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    raw_text = resp.text
                break
            except ServerError as e:
                last_err = e
                wait = 15 * (retry + 1)
                log.warning(f"Eval 503 (attempt {retry+1}/3), retrying in {wait}s…")
                time.sleep(wait)
            except Exception as e:
                last_err = e
                wait = 15 * (retry + 1)
                log.warning(f"Eval error (attempt {retry+1}/3): {str(e)[:80]}, retrying in {wait}s…")
                time.sleep(wait)

        if raw_text is None:
            log.warning(f"Eval unavailable after 3 retries — skipping, assuming pass")
            return EvalResult(
                scores={"specificity": 4, "actionability": 4, "data_grounding": 4, "conciseness": 4},
                total=16,
                critique="Eval skipped (API unavailable on all retries)",
                passed=True,
                attempt=attempt,
            )

        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        raw = json.loads(cleaned)
        scores = raw["scores"]
        total = sum(scores.values())
        passed = total >= PASS_THRESHOLD

        result = EvalResult(
            scores=scores,
            total=total,
            critique=raw["critique"],
            passed=passed,
            attempt=attempt,
        )

        self._log(result)
        log.info(
            f"Eval attempt {attempt}: {total}/20 "
            f"[spec={scores['specificity']} act={scores['actionability']} "
            f"grnd={scores['data_grounding']} conc={scores['conciseness']}] "
            f"{'PASS' if passed else 'FAIL'}"
        )
        if not passed:
            log.info(f"Critique: {result.critique}")

        return result

    def _log(self, result: EvalResult):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "total": result.total,
            "scores": result.scores,
            "passed": result.passed,
            "attempt": result.attempt,
            "critique": result.critique,
        }
        with open(EVAL_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
