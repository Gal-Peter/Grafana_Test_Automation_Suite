import time

import allure
import pytest
from playwright.sync_api import expect


def _wait_for_variable(api, uid: str, name: str, timeout_s: int = 15) -> dict | None:
    deadline = time.monotonic() + timeout_s
    while True:
        variables = api.get_dashboard(uid).json()["dashboard"].get("templating", {}).get("list", [])
        found = next((v for v in variables if v.get("name") == name), None)
        if found or time.monotonic() >= deadline:
            return found
        time.sleep(0.5)


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
class TestDashboardVariablesInUi:
    @pytest.mark.regression
    @allure.title("A custom variable added in the UI is saved with its values")
    def test_add_custom_variable(self, grafana_api, dashboard_factory, dashboard_page, dashboard_editor_page, page):
        dash = dashboard_factory()
        values = ["dev", "staging", "prod"]

        dashboard_page.open_by_uid(dash.uid)
        (dashboard_editor_page.start_editing()
         .add_custom_variable("env", ", ".join(values))
         .save_changes("add env variable"))

        variable = _wait_for_variable(grafana_api, dash.uid, "env")
        assert variable is not None, "The 'env' variable was not saved with the dashboard"
        assert variable["type"] == "custom"
        stored_text = str(variable)
        for value in values:
            assert value in stored_text, f"'{value}' missing from the saved variable: {variable}"

        dashboard_page.open_by_uid(dash.uid)
        expect(page.get_by_text("env", exact=True).first).to_be_visible()
