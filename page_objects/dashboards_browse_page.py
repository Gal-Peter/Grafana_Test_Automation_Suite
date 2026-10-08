from __future__ import annotations

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class DashboardsBrowsePage(BasePage):
    path = "/dashboards"

    @property
    def search_input(self):
        return self.page.get_by_role("textbox", name="Search for dashboards and folders")

    @step("Search dashboards for '{query}'")
    def search(self, query: str):
        self.search_input.fill(query)
        return self

    def result(self, title: str):
        return self.page.get_by_test_id(f"data-testid browse dashboards row {title}").or_(
            self.page.get_by_role("link", name=title, exact=True)).first
