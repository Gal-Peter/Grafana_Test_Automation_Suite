from __future__ import annotations

from page_objects.mobile.base_screen import BaseScreen
from utils.allure_helpers import step


class DashboardScreen(BaseScreen):
    @step("Open dashboard '{uid}'")
    def open_by_uid(self, uid: str):
        self.driver.get(f"{self.base_url}/d/{uid}")
        return self
