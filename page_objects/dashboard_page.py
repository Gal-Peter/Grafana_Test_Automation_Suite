from __future__ import annotations

from page_objects.components.panel import Panel
from page_objects.base_page import BasePage
from utils.allure_helpers import step


class DashboardPage(BasePage):
    @step("Open dashboard '{uid}'")
    def open_by_uid(self, uid: str):
        self.page.goto(f"/d/{uid}")
        return self

    def title_breadcrumb(self, title: str):
        """Grafana 13 shows the dashboard title as the last breadcrumb item (there is no title heading)."""
        return self.page.get_by_test_id(f"data-testid {title} breadcrumb")

    def panel(self, title: str) -> Panel:
        return Panel(self.page, title)
