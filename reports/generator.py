"""
SupplyWatch report generator.

Usage:
    from reports.generator import ReportGenerator
    gen = ReportGenerator()
    paths = gen.run()          # uses reports/output/ and today's date
    print(paths)               # {'md': '...', 'html': '...'}
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .evaluator import ReportEvaluator, MAX_RETRIES
from .prompt_template import build_prompt_pair

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS = [
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
]

# Gemini fallback (used only if OPENROUTER_API_KEY is absent)
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]
OUTPUT_DIR = Path(__file__).parent / "output"

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SupplyWatch Brief — {date}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 820px; margin: 48px auto; padding: 0 24px;
            color: #1a1a1a; line-height: 1.6; }}
    h1   {{ font-size: 1.5rem; border-bottom: 3px solid #d62828; padding-bottom: 8px; }}
    h2   {{ font-size: 1.15rem; margin-top: 2rem; color: #d62828; }}
    h3   {{ font-size: 1rem; margin-top: 1.4rem; }}
    ul, ol {{ padding-left: 1.4em; }}
    li   {{ margin-bottom: 4px; }}
    p    {{ margin: 0.6em 0; }}
    .meta {{ color: #666; font-size: 0.85rem; margin-bottom: 2rem; }}
    .eval-badge {{ display: inline-block; font-size: 0.75rem; padding: 2px 8px;
                   border-radius: 4px; margin-left: 8px; vertical-align: middle; }}
    .eval-pass {{ background: #d4edda; color: #155724; }}
    .eval-fail {{ background: #f8d7da; color: #721c24; }}
  </style>
</head>
<body>
  <h1>SupplyWatch — Weekly Disruption Brief
    <span class="eval-badge {eval_class}">{eval_label}</span>
  </h1>
  <p class="meta">Week ending {date} &nbsp;|&nbsp; Quality score: {eval_score}/20 &nbsp;|&nbsp; SupplyWatch Beta</p>
  {body}
</body>
</html>
"""


def _markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    html_lines: list[str] = []
    in_ul = in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False
        if in_ol:
            html_lines.append("</ol>")
            in_ol = False

    for line in lines:
        if line.startswith("## "):
            close_lists()
            html_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("### "):
            close_lists()
            html_lines.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                close_lists()
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{line[2:].strip()}</li>")
        elif line and line[0].isdigit() and ". " in line[:4]:
            if not in_ol:
                close_lists()
                html_lines.append("<ol>")
                in_ol = True
            html_lines.append(f"<li>{line.split('. ', 1)[1].strip()}</li>")
        elif line.strip() == "":
            close_lists()
            html_lines.append("")
        else:
            close_lists()
            html_lines.append(f"<p>{line.strip()}</p>")

    close_lists()
    return "\n".join(html_lines)


class ReportGenerator:
    def __init__(
        self,
        scorer_output_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        report_date: date | None = None,
    ):
        or_key = os.getenv("OPENROUTER_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")

        if or_key:
            from openai import OpenAI
            self.client = OpenAI(base_url=OPENROUTER_BASE, api_key=or_key)
            self._backend = "openrouter"
            self._models = OPENROUTER_MODELS
            log.info("Backend: OpenRouter")
        elif gemini_key:
            from google import genai as _genai
            self.client = _genai.Client(api_key=gemini_key)
            self._backend = "gemini"
            self._models = GEMINI_MODELS
            log.info("Backend: Gemini (fallback)")
        else:
            raise EnvironmentError("Set OPENROUTER_API_KEY (or GEMINI_API_KEY) in .env")

        self._model = self._pick_model()
        self.evaluator = ReportEvaluator(self.client, self._model, self._backend)
        self.output_dir = Path(output_dir or OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_date = report_date or date.today()
        self._scorer_path = Path(scorer_output_path) if scorer_output_path else None

    def _pick_model(self) -> str:
        """Skip ping — _call_llm handles fallback on actual failures."""
        log.info(f"Using model: {self._models[0]}")
        return self._models[0]

    def load_scorer_output(self) -> list[dict[str, Any]]:
        if self._scorer_path:
            with open(self._scorer_path) as f:
                return json.load(f)
        raise NotImplementedError(
            "Live API ingestion not wired yet — pass scorer_output_path for now"
        )

    def _raw_call(self, model: str, content: str) -> str:
        """Single LLM call, backend-agnostic."""
        if self._backend == "openrouter":
            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
            )
            return resp.choices[0].message.content
        else:
            resp = self.client.models.generate_content(model=model, contents=content)
            return resp.text

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        import time
        combined = f"{system_prompt}\n\n---\n\n{user_prompt}"
        waits = [15, 30, 60]
        for model in self._models:
            for attempt, wait in enumerate(waits):
                try:
                    result = self._raw_call(model, combined)
                    if model != self._model:
                        log.info(f"Switched to: {model}")
                        self._model = model
                    return result
                except Exception as e:
                    err = str(e)
                    if "429" in err:
                        log.warning(f"{model} quota — skipping")
                        break
                    log.warning(f"{model} error (attempt {attempt+1}/{len(waits)}), retrying in {wait}s…")
                    time.sleep(wait)
        raise EnvironmentError("All models failed — check API keys or try again later")

    def generate_markdown(self, minerals: list[dict[str, Any]]) -> tuple[str, int]:
        """
        Generates the report with a self-evaluation retry loop.
        Returns (final_markdown, final_score).
        Retries up to MAX_RETRIES times if the report scores below the pass threshold,
        appending the evaluator's critique to the prompt on each retry.
        """
        system_prompt, user_prompt = build_prompt_pair(minerals, self.report_date)
        best_md = ""
        best_score = 0

        for attempt in range(MAX_RETRIES + 1):
            markdown = self._call_llm(system_prompt, user_prompt)
            result = self.evaluator.evaluate(markdown, minerals, attempt=attempt)

            if result.total > best_score:
                best_md, best_score = markdown, result.total

            if result.passed:
                log.info(f"Report passed on attempt {attempt}: {result.total}/20")
                return best_md, best_score

            if attempt < MAX_RETRIES:
                log.info(f"Attempt {attempt} scored {result.total}/20 — retrying with critique")
                user_prompt = (
                    user_prompt
                    + f"\n\n---\nQUALITY CRITIQUE FROM PREVIOUS ATTEMPT (address these):\n{result.critique}"
                )

        log.warning(f"Max retries reached. Best score: {best_score}/20")
        return best_md, best_score

    def write_outputs(self, markdown: str, eval_score: int) -> dict[str, Path]:
        date_str = self.report_date.isoformat()
        md_path = self.output_dir / f"{date_str}.md"
        html_path = self.output_dir / f"{date_str}.html"

        md_path.write_text(markdown, encoding="utf-8")

        body_html = _markdown_to_html(markdown)
        passed = eval_score >= 16
        full_html = HTML_TEMPLATE.format(
            date=date_str,
            body=body_html,
            eval_score=eval_score,
            eval_class="eval-pass" if passed else "eval-fail",
            eval_label=f"Quality {eval_score}/20",
        )
        html_path.write_text(full_html, encoding="utf-8")

        return {"md": md_path, "html": html_path}

    def run(self, scorer_output_path: str | Path | None = None) -> dict[str, Path]:
        if scorer_output_path:
            self._scorer_path = Path(scorer_output_path)
        minerals = self.load_scorer_output()
        markdown, eval_score = self.generate_markdown(minerals)
        return self.write_outputs(markdown, eval_score)
