import allure
import pytest
from selenium.webdriver.support.ui import WebDriverWait

from utils.data_loader import load_cases


@allure.epic("Grafana")
@allure.feature("Mobile web - Authentication")
@pytest.mark.mobile
@pytest.mark.no_auth
class TestMobileLogin:
    @pytest.mark.smoke
    @allure.title("Mobile: valid login succeeds")
    def test_valid_login(self, mobile_login_screen, settings):
        screen = mobile_login_screen.open().login(settings.username, settings.password)
        screen.dismiss_password_prompt()
        WebDriverWait(screen.driver, 30).until(lambda d: "/login" not in d.current_url)
        assert "/login" not in screen.driver.current_url

    @pytest.mark.regression
    @pytest.mark.parametrize("case", load_cases("login_invalid"))
    def test_invalid_login(self, case, mobile_login_screen):
        allure.dynamic.title(f"Mobile: invalid login rejected - {case['id']}")
        mobile_login_screen.open().login(case["username"], case["password"])
        assert mobile_login_screen.has_text(case["expected_error"], timeout=10), \
            f"Expected message '{case['expected_error']}' not shown"
