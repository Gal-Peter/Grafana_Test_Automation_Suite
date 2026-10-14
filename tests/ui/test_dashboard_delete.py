import time

import allure
import pytest
from playwright.sync_api import expect


def _wait_until_gone(api, uid: str, timeout_s: int = 15) -> int:
    deadline = time.monotonic() + timeout_s
    while True:
        status = api.get_dashboard(uid).status_code
        if status == 404 or time.monotonic() >= deadline:
            return status
        time.sleep(0.5)


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
class TestDashboardDeleteInUi:
    @pytest.mark.smoke
    @allure.title("A dashboard can be deleted from its settings")
    def test_delete_from_settings(self, grafana_api, dashboard_factory, dashboard_page, dashboard_editor_page,
                                  dashboards_browse_page):
        dash = dashboard_factory()
        assert grafana_api.get_dashboard(dash.uid).status_code == 200

        dashboard_page.open_by_uid(dash.uid)
        dashboard_editor_page.start_editing().open_settings().delete_dashboard("delete")

        assert _wait_until_gone(grafana_api, dash.uid) == 404, "The dashboard still exists after deleting it"
        dashboards_browse_page.open().search(dash.title)
        expect(dashboards_browse_page.result(dash.title)).to_have_count(0)

    @pytest.mark.regression
    @allure.title("Deleting needs the right confirmation text")
    def test_wrong_confirmation_keeps_dashboard(self, grafana_api, dashboard_factory, dashboard_page,
                                                dashboard_editor_page, page):
        dash = dashboard_factory()

        dashboard_page.open_by_uid(dash.uid)
        dashboard_editor_page.start_editing().open_settings().delete_dashboard("not-the-word")

        page.wait_for_timeout(1500)  # give a (wrong) delete time to happen before checking
        assert grafana_api.get_dashboard(dash.uid).status_code == 200, "Dashboard was deleted without the confirmation"
