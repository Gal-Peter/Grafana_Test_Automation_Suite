"""CLI: parse allure-results and write the AI-analysed HTML report.

    python -m ai.generate_report
    python -m ai.generate_report --results allure-results --output logs/ai_report.html --no-ai
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai.allure_parser import load_run
from ai.report_analyzer import analyse
from ai.report_generator import render_html
from utils.settings import get_settings


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description="Generate the AI-analysed HTML report from Allure results")
    ap.add_argument("--results", default=str(s.allure_dir), help="allure-results directory")
    ap.add_argument("--output", default=str(s.ai_report_path), help="HTML file to write")
    ap.add_argument("--title", default="Grafana Test Run: AI Analysis")
    ap.add_argument("--no-ai", action="store_true", help="skip the LLM call (rule-based analysis only)")
    args = ap.parse_args(argv)

    results = Path(args.results)
    run = load_run(results)
    if not run.cases:
        print(f"No *-result.json files found in {results}. Run the tests first.", file=sys.stderr)
        return 2

    use_ai = s.ai_report_analysis and not args.no_ai
    summary, analysis = analyse(run, s, use_ai=use_ai)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(summary, analysis, args.title), encoding="utf-8")
    print(f"AI report written: {out}  ({analysis['source']} analysis, {summary['total']} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
