"""Page Object base for mobile-browser tests (Selenium/Appium locators)."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.allure_helpers import step


class BaseScreen:
    path = "/"

    def __init__(self, driver, base_url: str, timeout: int = 20):
        self.driver = driver
        self.base_url = base_url
        self._wait = WebDriverWait(driver, timeout)

    @step("Open {self.path}")
    def open(self, path: str | None = None):
        self.driver.get(f"{self.base_url}{path or self.path}")
        return self

    def wait_visible(self, css: str):
        return self._wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))

    def wait_text(self, text: str):
        locator = (By.XPATH, f'//*[contains(normalize-space(.), "{text}")]')
        return self._wait.until(EC.presence_of_element_located(locator))

    def has_text(self, text: str, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, f'//*[contains(normalize-space(.), "{text}")]')))
            return True
        except Exception:
            return False

    @property
    def current_path(self) -> str:
        return self.driver.current_url.replace(self.base_url, "")

    def has_horizontal_overflow(self) -> bool:
        """True when the page scrolls sideways - a classic responsive-layout defect."""
        return bool(self.driver.execute_script(
            "return document.documentElement.scrollWidth > window.innerWidth + 1;"))
