"""
Tests the report generator against mock scorer data.

Run from the supplywatch/ root:
    ANTHROPIC_API_KEY=sk-... python -m pytest tests/ -v

Or without pytest (just checks outputs exist):
    ANTHROPIC_API_KEY=sk-... python tests/test_generator.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

# Make sure the package is importable when run from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_DATA = Path(__file__).parent / "sample_scorer_output.json"
FIXED_DATE = date(2026, 6, 4)


def _make_generator(output_dir: Path):
    from reports.generator import ReportGenerator
    return ReportGenerator(
        scorer_output_path=SAMPLE_DATA,
        output_dir=output_dir,
        report_date=FIXED_DATE,
    )


def test_output_files_created():
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = _make_generator(Path(tmpdir))
        paths = gen.run()

        assert paths["md"].exists(), "Markdown output not created"
        assert paths["html"].exists(), "HTML output not created"
        assert paths["md"].stat().st_size > 500, "Markdown file suspiciously small"
        assert paths["html"].stat().st_size > 500, "HTML file suspiciously small"
        print(f"\n  md  : {paths['md']}")
        print(f"  html: {paths['html']}")


def test_output_contains_required_sections():
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = _make_generator(Path(tmpdir))
        paths = gen.run()

        content = paths["md"].read_text()
        for section in [
            "Executive Summary",
            "What Moved",
            "Risk Outlook",
            "Recommended Actions",
        ]:
            assert section in content, f"Section '{section}' missing from output"


def test_html_is_valid_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = _make_generator(Path(tmpdir))
        paths = gen.run()

        html = paths["html"].read_text()
        assert "<!DOCTYPE html>" in html
        assert "<h2>" in html
        assert "SupplyWatch" in html


def test_prompt_template_builds_without_api():
    """Smoke-tests prompt construction without making an API call."""
    from reports.prompt_template import build_prompt_pair

    with open(SAMPLE_DATA) as f:
        minerals = json.load(f)

    system, user = build_prompt_pair(minerals, FIXED_DATE)
    assert "procurement" in system.lower()
    assert "Gallium" in user
    assert "Executive Summary" in user
    assert "Recommended Actions" in user


if __name__ == "__main__":
    # Quick smoke run — calls the real API once
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    output_dir = Path(__file__).parent.parent / "reports" / "output"
    gen = _make_generator(output_dir)
    print("Calling Claude API…")
    paths = gen.run()
    print(f"\nDone.\n  Markdown : {paths['md']}\n  HTML     : {paths['html']}\n")
    print("--- Markdown preview (first 60 lines) ---")
    lines = paths["md"].read_text().splitlines()
    print("\n".join(lines[:60]))
