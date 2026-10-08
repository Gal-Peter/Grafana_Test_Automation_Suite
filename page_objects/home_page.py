from __future__ import annotations

from page_objects.base_page import BasePage


class HomePage(BasePage):
    path = "/"

    @property
    def welcome_text(self):
        """The h1 is a time-of-day greeting ('Good evening.'), so assert on the stable welcome text."""
        return self.page.get_by_text("Welcome to Grafana").first

    @property
    def greeting_heading(self):
        return self.page.get_by_role("heading", level=1)
