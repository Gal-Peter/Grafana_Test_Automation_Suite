from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from page_objects.mobile.base_screen import BaseScreen
from utils.allure_helpers import step

USERNAME = "input[name='user'], [data-testid='data-testid Username input field']"
PASSWORD = "input[name='password'], [data-testid='data-testid Password input field']"


class LoginScreen(BaseScreen):
    path = "/login"

    @step("Log in as '{username}'")
    def login(self, username: str, password: str):
        self.wait_visible(USERNAME).send_keys(username)
        field = self.wait_visible(PASSWORD)
        field.send_keys(password)
        field.send_keys(Keys.ENTER)  # Enter avoids the on-screen keyboard covering the button
        return self

    @step("Skip the 'Update your password' prompt if Grafana shows it")
    def dismiss_password_prompt(self, wait_s: int = 5):
        try:
            button = WebDriverWait(self.driver, wait_s).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Skip']")))
        except Exception:
            return self  # no prompt
        button.click()
        return self
