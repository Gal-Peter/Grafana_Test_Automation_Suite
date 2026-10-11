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

    @step("Finish login (skip the 'Update your password' prompt if Grafana shows it)")
    def dismiss_password_prompt(self, wait_s: int = 45):
        """After submitting, Grafana either leaves /login or shows a Skip button on the same URL.
        The emulator is slow, so wait for whichever happens first instead of a short fixed wait."""
        def done_or_prompt(driver):
            if "/login" not in driver.current_url:
                return "done"
            buttons = driver.find_elements(By.XPATH, "//button[normalize-space()='Skip']")
            return buttons[0] if buttons else False

        try:
            outcome = WebDriverWait(self.driver, wait_s).until(done_or_prompt)
        except Exception:
            return self  # neither happened; the caller's assertion will report it
        if outcome != "done":
            # JS click: the on-screen keyboard or viewport can cover the button
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", outcome)
        return self
