"""
SupplyWatch weekly pipeline — single entry point for cron.

Runs every Monday via crontab:
    0 9 * * 1 cd /home/malhar/cli/supplywatch && python run_weekly.py >> logs/cron.log 2>&1

What it does:
  1. Generates the report (with self-eval loop)
  2. Posts to Substack + Reddit
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent / "logs"


def main():
    LOGS_DIR.mkdir(exist_ok=True)
    log.info(f"=== SupplyWatch weekly run — {date.today()} ===")

    # Step 1: fetch live signals
    log.info("Step 1/3: Fetching live commodity signals…")
    try:
        from live_scorer import build_scorer_output
        minerals = build_scorer_output()
        log.info(f"Live signals fetched for {[m['mineral'] for m in minerals]}")
    except Exception as e:
        log.warning(f"Live scorer failed ({e}) — falling back to sample data")
        import json
        minerals = json.loads(
            (Path(__file__).parent / "tests" / "sample_scorer_output.json").read_text()
        )

    # Step 2: generate report
    log.info("Step 2/3: Generating report…")
    try:
        from reports.generator import ReportGenerator
        gen = ReportGenerator()
        markdown, eval_score = gen.generate_markdown(minerals)
        paths = gen.write_outputs(markdown, eval_score)
        log.info(f"Report written: {paths['md']}")
    except Exception as e:
        log.error(f"Report generation failed: {e}")
        sys.exit(1)

    # Step 3a: email the brief to whoever is watching
    md_text = paths["md"].read_text()
    report_date_str = paths["md"].stem
    try:
        from pipeline.email_sender import EmailSender
        EmailSender().prompt_and_send(md_text, report_date_str)
    except Exception as e:
        log.warning(f"Email skipped: {e}")

    # Step 3b: post to Substack + Reddit
    log.info("Step 3/3: Posting pipeline…")
    try:
        from pipeline.scheduler import run as pipeline_run
        pipeline_run()
    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        sys.exit(1)

    log.info("=== Weekly run complete ===")


if __name__ == "__main__":
    main()
