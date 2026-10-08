from __future__ import annotations

from page_objects.components.alert import Alert
from page_objects.base_page import BasePage
from utils.allure_helpers import step


class DataSourcesPage(BasePage):
    path = "/connections/datasources"

    def datasource_link(self, name: str):
        return self.page.get_by_role("link", name=name).first

    @step("Open data source editor for '{uid}'")
    def open_editor(self, uid: str):
        self.page.goto(f"/connections/datasources/edit/{uid}")
        return self

    @step("Click Save & test")
    def save_and_test(self):
        self.page.get_by_role("button", name="Save & test").click()
        return Alert(self.page, "success")
