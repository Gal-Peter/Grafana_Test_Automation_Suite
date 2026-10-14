"""Page Object Model base. Pages hold locators + actions; tests hold the assertions."""
from __future__ import annotations

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from utils.allure_helpers import step


class BasePage:
    path: str = "/"

    def __init__(self, page: Page):
        self.page = page

    @step("Open {self.path}")
    def open(self, path: str | None = None):
        self.page.goto(path or self.path)
        return self

    # -- helpers -------------------------------------------------------------
    def _where_are_we(self) -> str:
        """What the page looks like right now: goes into the error so one failing run explains itself."""
        try:
            main = self.page.locator("main")
            # the side menu fills the first lines of a body snapshot, so prefer the page content when there is one
            snapshot = (main if main.count() else self.page.locator("body")).aria_snapshot()[:3500]
        except Exception as exc:  # the page itself may be gone
            snapshot = f"(no snapshot: {exc})"
        return f"URL: {self.page.url}\n--- page content (aria snapshot) ---\n{snapshot}"

    def _click(self, locator: Locator, what: str, timeout_ms: int | None = None):
        try:
            locator.click(timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise AssertionError(f"Could not click {what}.\n{self._where_are_we()}") from exc
