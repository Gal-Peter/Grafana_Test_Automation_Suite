"""Importing a dashboard from JSON. Locators come from a Playwright codegen recording on Grafana 13.2.2."""
from __future__ import annotations

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class ImportPage(BasePage):
    path = "/dashboard/import"

    @property
    def json_box(self):
        return self.page.get_by_test_id("data-testid-import-dashboard-textarea")

    @property
    def import_button(self):
        return self.page.get_by_test_id("data-testid-import-dashboard-submit")

    @step("Paste the dashboard JSON and click Load")
    def load_json(self, text: str):
        self.open()
        self.json_box.fill(text)
        self._click(self.page.get_by_test_id("data-testid-load-dashboard"), "'Load'")
        return self

    @step("Import the loaded dashboard")
    def submit(self, uid: str):
        self._click(self.import_button, "'Import'")
        try:
            self.page.wait_for_url(f"**/d/{uid}/**", timeout=15000)
        except Exception as exc:
            raise AssertionError(f"The dashboard did not open after importing.\n{self._where_are_we()}") from exc
        return self

    @step("Import the dashboard from JSON")
    def import_json(self, text: str, uid: str):
        return self.load_json(text).submit(uid)
