from __future__ import annotations

from playwright.sync_api import Page

from page_objects.components.base_component import BaseComponent


class Alert(BaseComponent):
    def __init__(self, page: Page, severity: str = "success"):
        super().__init__(page, page.get_by_test_id(f"data-testid Alert {severity}"))
