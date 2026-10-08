import json

import pytest

from ai.allure_parser import load_run
from ai.report_analyzer import analyse, classify
from ai.report_generator import render_html
from utils.settings import get_settings

pytestmark = pytest.mark.unit


def _write(tmp_path, name, status, message="", browser="chromium", feature="Dashboards"):
    data = {"uuid": name, "historyId": name, "name": name, "status": status, "start": 1000, "stop": 3000,
            "labels": [{"name": "feature", "value": feature}],
            "parameters": [{"name": "browser", "value": browser}]}
    if message:
        data["statusDetails"] = {"message": message, "trace": message}
    (tmp_path / f"{name}-result.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("message,category", [
    ("requests.exceptions.ConnectionError: refused", "Environment / connectivity"),
    ("AssertionError: Locator expected to be visible", "Locator / timing"),
    ("AssertionError: assert 200 == 400", "Assertion"),
    ("something odd", "Unclassified"),
])
def test_failure_classification(message, category):
    assert classify(message) == category


def test_report_end_to_end_is_escaped_and_complete(tmp_path):
    _write(tmp_path, "ok-1", "passed")
    _write(tmp_path, "bad-1", "failed", "AssertionError: Locator expected to be visible <script>x()</script>")
    _write(tmp_path, "skip-1", "skipped")
    (tmp_path / "broken-result.json").write_text("{not json", encoding="utf-8")  # must be ignored

    run = load_run(tmp_path)
    assert len(run.cases) == 3

    summary, analysis = analyse(run, get_settings(), use_ai=False)
    assert summary["counts"]["failed"] == 1 and summary["pass_rate"] == 50.0
    assert analysis["risk"] in {"medium", "high"}

    html = render_html(summary, analysis)
    assert "Failure analysis" in html and "Suggested improvements" in html
    assert "<script>x()</script>" not in html and "&lt;script&gt;" in html


def test_empty_results_dir_yields_no_cases(tmp_path):
    assert load_run(tmp_path).cases == []
