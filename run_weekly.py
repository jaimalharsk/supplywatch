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

SCORER_DATA = Path(__file__).parent / "tests" / "sample_scorer_output.json"
LOGS_DIR    = Path(__file__).parent / "logs"


def main():
    LOGS_DIR.mkdir(exist_ok=True)
    log.info(f"=== SupplyWatch weekly run — {date.today()} ===")

    # Step 1: generate report
    log.info("Step 1/2: Generating report…")
    try:
        from reports.generator import ReportGenerator
        gen   = ReportGenerator(scorer_output_path=SCORER_DATA)
        paths = gen.run()
        log.info(f"Report written: {paths['md']}")
    except Exception as e:
        log.error(f"Report generation failed: {e}")
        sys.exit(1)

    # Step 2: post to Substack + Reddit
    log.info("Step 2/2: Posting pipeline…")
    try:
        from pipeline.scheduler import run as pipeline_run
        pipeline_run()
    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        sys.exit(1)

    log.info("=== Weekly run complete ===")


if __name__ == "__main__":
    main()
