import time

import allure
import pytest
from playwright.sync_api import expect

from utils.factories import unique_name


def _wait_for_dashboard(api, title: str, timeout_s: int = 15) -> list[str]:
    deadline = time.monotonic() + timeout_s
    while True:
        uids = api.find_dashboard_uids(title)
        if uids or time.monotonic() >= deadline:
            return uids
        time.sleep(0.5)


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
class TestDashboardCreateInUi:
    @pytest.mark.smoke
    @allure.title("A dashboard created in the UI is saved, listed and can be opened")
    def test_create_dashboard(self, grafana_api, tracker, dashboard_editor_page, dashboards_browse_page,
                              dashboard_page):
        title = unique_name("AUTOMATION-ui-dash")
        tracker.register(grafana_api.delete_dashboards_titled, title)  # runs even if the test fails half-way

        dashboard_editor_page.open_new_from_ui().add_visualization()
        dashboard_editor_page.save(title, "created by automation")

        uids = _wait_for_dashboard(grafana_api, title)
        assert len(uids) == 1, f"Dashboard '{title}' was not saved (found {len(uids)})"

        dashboard_editor_page.back_to_dashboards()
        dashboards_browse_page.search(title)
        expect(dashboards_browse_page.result(title)).to_be_visible()

        dashboard_page.open_by_uid(uids[0])
        expect(dashboard_page.title_breadcrumb(title)).to_be_visible()
        expect(dashboard_page.panel("New panel").header).to_be_visible()
