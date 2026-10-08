"""pytest hooks: expose phase reports, keep allure-results clean, write Allure environment info."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from utils.grafana_client import GrafanaClient
from utils.settings import get_settings


def _is_xdist_worker(config) -> bool:
    return hasattr(config, "workerinput")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Expose each phase's report on the item so fixtures can tell whether the test failed."""
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())


def pytest_sessionstart(session):
    """Empty allure-results (the folder itself stays, which matters for Docker bind mounts)."""
    if _is_xdist_worker(session.config) or os.getenv("KEEP_ALLURE_RESULTS"):
        return
    results = session.config.getoption("allure_report_dir", default=None)
    if not results or not Path(results).is_dir():
        return
    for entry in Path(results).iterdir():
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()


def pytest_sessionfinish(session):
    """environment.properties makes the Allure report show what was tested."""
    if _is_xdist_worker(session.config):
        return
    results = session.config.getoption("allure_report_dir", default=None)
    if not results:
        return
    s = get_settings()
    try:
        version = GrafanaClient(s.base_url, s.username, s.password, s.testdata_type).health().get("version", "unknown")
    except Exception:
        version = "unreachable"
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "environment.properties"), "w", encoding="utf-8") as fh:
        fh.write(f"grafana.url={s.base_url}\ngrafana.version={version}\n")
        fh.write(f"trace={s.trace}\nvideo={s.video}\n")
