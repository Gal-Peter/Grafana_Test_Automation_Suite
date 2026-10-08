import re

import allure
import pytest
from playwright.sync_api import expect

from utils.data_loader import load_cases


@allure.epic("Grafana")
@allure.feature("Authentication")
@pytest.mark.no_auth
class TestLogin:
    @pytest.mark.smoke
    @allure.title("Valid credentials log the user in")
    def test_valid_login(self, login_page, home_page, settings):
        login_page.open().login(settings.username, settings.password)
        login_page.dismiss_password_prompt()
        expect(login_page.page).not_to_have_url(re.compile(r"/login"))
        expect(home_page.welcome_text).to_be_visible()

    @pytest.mark.regression
    @pytest.mark.parametrize("case", load_cases("login_invalid"))
    def test_invalid_login(self, case, login_page):
        allure.dynamic.title(f"Invalid login rejected: {case['id']}")
        login_page.open().login(case["username"], case["password"])
        expect(login_page.message(case["expected_error"])).to_be_visible()
        expect(login_page.page).to_have_url(re.compile(r"/login"))

    @pytest.mark.regression
    @allure.title("Unauthenticated user is redirected to login")
    def test_redirect_when_unauthenticated(self, page):
        page.goto("/dashboards")
        expect(page).to_have_url(re.compile(r"/login"))
