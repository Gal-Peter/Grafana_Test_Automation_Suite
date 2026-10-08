from __future__ import annotations

from playwright.sync_api import Locator, Page


class BaseComponent:
    """Reusable UI fragment (Component Object pattern) that is scoped to a root locator."""

    def __init__(self, page: Page, root: Locator):
        self.page = page
        self.root = root
