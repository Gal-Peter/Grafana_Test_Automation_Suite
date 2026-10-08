from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class LoginPage(BasePage):
    path = "/login"

    @property
    def username_input(self):
        return self.page.get_by_test_id("data-testid Username input field")

    @property
    def password_input(self):
        return self.page.get_by_test_id("data-testid Password input field")

    @property
    def submit_button(self):
        return self.page.get_by_test_id("data-testid Login button")

    def message(self, text: str):
        return self.page.get_by_text(text)

    @step("Log in as '{username}'")
    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_button.click()
        return self

    @step("Skip the 'Update your password' prompt if Grafana shows it")
    def dismiss_password_prompt(self, wait_ms: int = 4000):
        """Grafana asks to change the default admin/admin password right after login. Skip is a BUTTON."""
        skip = self.page.get_by_role("button", name="Skip")
        try:
            skip.wait_for(state="visible", timeout=wait_ms)
        except PlaywrightTimeoutError:
            return self  # no prompt: password was already changed
        skip.click()
        return self
