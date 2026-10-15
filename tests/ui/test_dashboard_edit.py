import re
import time

import allure
import pytest
from playwright.sync_api import expect

from utils.factories import unique_name


def _wait_for_title(api, uid: str, title: str, timeout_s: int = 15) -> dict:
    deadline = time.monotonic() + timeout_s
    while True:
        stored = api.get_dashboard(uid).json()["dashboard"]
        if stored["title"] == title or time.monotonic() >= deadline:
            return stored
        time.sleep(0.5)


def _version_count(api, uid: str) -> int:
    """History entries: more reliable than the 'version' field, which Grafana 13 can report differently per setup."""
    data = api.request("GET", f"/api/dashboards/uid/{uid}/versions").json()
    return len(data.get("versions", data) if isinstance(data, dict) else data)


def _panel_titles(dashboard: dict) -> list[str]:
    """Panels can sit at the top level or inside rows/groups depending on the layout."""
    titles = []
    for panel in dashboard.get("panels", []):
        titles.append(panel.get("title"))
        titles.extend(p.get("title") for p in panel.get("panels", []))
    return titles


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
class TestDashboardEditInUi:
    @pytest.mark.smoke
    @allure.title("An existing dashboard can be renamed, get a new panel and be saved")
    def test_rename_and_add_panel(self, grafana_api, dashboard_factory, dashboard_page, dashboard_editor_page):
        dash = dashboard_factory()
        versions_before = _version_count(grafana_api, dash.uid)
        new_title, new_panel = unique_name("AUTOMATION-renamed-ui"), unique_name("panel")

        dashboard_page.open_by_uid(dash.uid)
        (dashboard_editor_page.start_editing()
         .rename(new_title)
         .add_panel(new_panel, "added by automation")
         .save_changes("automation edit"))

        stored = _wait_for_title(grafana_api, dash.uid, new_title)
        assert stored["title"] == new_title, "The new title was not saved"
        assert new_panel in _panel_titles(stored), f"Panel '{new_panel}' not in saved dashboard: {_panel_titles(stored)}"
        versions_after = _version_count(grafana_api, dash.uid)
        assert versions_after > versions_before, \
            f"Saving did not add a version ({versions_before} -> {versions_after}); stored version: {stored.get('version')}"

        dashboard_page.open_by_uid(dash.uid)
        expect(dashboard_page.title_breadcrumb(new_title)).to_be_visible()
        expect(dashboard_page.panel(new_panel).header).to_be_visible()
        for original in dash.panel_titles:  # the existing panels are untouched
            expect(dashboard_page.panel(original).header).to_be_visible()


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
@pytest.mark.no_auth
class TestViewerCannotEdit:
    @pytest.mark.regression
    @allure.title("A Viewer sees the dashboard but has no Edit button")
    def test_viewer_has_no_edit_button(self, user_factory, dashboard_factory, login_page, dashboard_page, page):
        viewer = user_factory("Viewer")
        dash = dashboard_factory()

        login_page.open().login(viewer.login, viewer.password)
        login_page.dismiss_password_prompt(wait_ms=1500)
        expect(page).not_to_have_url(re.compile(r"/login"))

        dashboard_page.open_by_uid(dash.uid)
        expect(dashboard_page.title_breadcrumb(dash.title)).to_be_visible()
        expect(page.get_by_test_id("data-testid Edit dashboard button")).to_have_count(0)
