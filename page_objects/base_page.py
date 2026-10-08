"""Page Object Model base. Pages hold locators + actions; tests hold the assertions."""
from __future__ import annotations

from playwright.sync_api import Page

from utils.allure_helpers import step


class BasePage:
    path: str = "/"

    def __init__(self, page: Page):
        self.page = page

    @step("Open {self.path}")
    def open(self, path: str | None = None):
        self.page.goto(path or self.path)
        return self
