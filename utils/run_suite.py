"""One-command entry point (used by Docker, Jenkins and GitHub Actions; works on Windows too):
runs pytest, then ALWAYS generates the AI report, and exits with pytest's exit code.

    python -m utils.run_suite                      # PYTEST_ARGS or the default below
    python -m utils.run_suite -m smoke --browser firefox
"""
from __future__ import annotations

import os
import shlex
import sys

DEFAULT_ARGS = '-m "not mobile and not ai"'


def main() -> int:
    import pytest

    args = sys.argv[1:] or shlex.split(os.environ.get("PYTEST_ARGS", DEFAULT_ARGS))
    code = int(pytest.main(args))
    try:
        from ai.generate_report import main as report

        report([])
    except Exception as exc:  # reporting must never hide the real test result
        print(f"AI report generation failed: {exc}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
