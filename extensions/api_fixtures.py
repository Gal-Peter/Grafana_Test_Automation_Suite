"""API-level fixtures: client, health gate, cleanup tracker, resource factories."""
from __future__ import annotations

from dataclasses import dataclass

import pytest
import requests

from utils.dashboard_builder import DashboardBuilder
from utils.factories import unique_name
from utils.grafana_client import GrafanaApiError, GrafanaClient
from utils.resource_tracker import ResourceTracker
from utils.settings import Settings, get_settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def grafana_client(settings) -> GrafanaClient:
    return GrafanaClient(settings.base_url, settings.username, settings.password, settings.testdata_type)


@pytest.fixture(scope="session")
def grafana_is_up(grafana_client, settings) -> dict:
    """Fail fast with a clear message. Only requested by Grafana-dependent fixtures, so unit tests don't need Grafana."""
    try:
        return grafana_client.wait_until_healthy(settings.startup_wait_s)
    except (requests.RequestException, GrafanaApiError):
        pytest.exit(f"Grafana is not reachable at {settings.base_url}. Start it first.", returncode=1)


@pytest.fixture(scope="session")
def grafana_api(grafana_client, grafana_is_up) -> GrafanaClient:
    return grafana_client


@pytest.fixture(scope="session")
def automation_folder(grafana_api):
    """All test content lives in one throw-away folder; never touches your real dashboards."""
    folder = grafana_api.create_folder(unique_name("AUTOMATION"))
    yield folder
    grafana_api.delete_folder(folder["uid"])


@pytest.fixture
def tracker():
    t = ResourceTracker()
    yield t
    t.cleanup()


@dataclass
class CreatedDashboard:
    uid: str
    title: str
    panel_titles: list[str]


@pytest.fixture
def dashboard_factory(grafana_api, automation_folder, tracker):
    def _create(builder: DashboardBuilder | None = None) -> CreatedDashboard:
        b = builder or DashboardBuilder()
        if not b.has_folder:
            b.in_folder(automation_folder["uid"])
        grafana_api.create_dashboard(b.build())
        tracker.register(grafana_api.delete_dashboard, b.uid)
        return CreatedDashboard(uid=b.uid, title=b.title, panel_titles=b.panel_titles)

    return _create


@pytest.fixture
def testdata_datasource(grafana_api, tracker):
    ds = grafana_api.create_testdata_datasource(unique_name("auto-testdata"))
    tracker.register(grafana_api.delete_datasource, ds["uid"])
    return ds


@dataclass
class TestUser:
    __test__ = False  # not a pytest class
    id: int
    login: str
    password: str
    role: str
    client: GrafanaClient


@pytest.fixture
def user_factory(grafana_api, tracker):
    """Create a throw-away user with a given org role; deleted automatically after the test."""
    def _create(role: str) -> TestUser:
        login = unique_name(f"auto-{role.lower()}")
        password = unique_name("Pw")
        created = grafana_api.create_user(login, password)
        tracker.register(grafana_api.delete_user, created["id"])
        grafana_api.set_org_role(created["id"], role)
        return TestUser(created["id"], login, password, role, grafana_api.as_user(login, password))

    return _create
