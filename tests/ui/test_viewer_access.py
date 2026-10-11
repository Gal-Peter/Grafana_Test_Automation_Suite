import re

import allure
import pytest
from playwright.sync_api import expect


@allure.epic("Grafana")
@allure.feature("Users & permissions (UI)")
@pytest.mark.no_auth
class TestViewerAccess:
    """Log in through the real login form as a low-privilege user and check what the UI lets them see."""

    @pytest.fixture
    def viewer_session(self, user_factory, login_page):
        user = user_factory("Viewer")
        login_page.open().login(user.login, user.password)
        login_page.dismiss_password_prompt(wait_ms=1500)
        expect(login_page.page).not_to_have_url(re.compile(r"/login"))
        return user

    @pytest.mark.smoke
    @allure.title("Viewer can open a dashboard shared in a folder")
    def test_viewer_can_view_dashboard(self, viewer_session, dashboard_factory, dashboard_page):
        dash = dashboard_factory()
        dashboard_page.open_by_uid(dash.uid)
        expect(dashboard_page.title_breadcrumb(dash.title)).to_be_visible()
        for title in dash.panel_titles:
            expect(dashboard_page.panel(title).header).to_be_visible()

    @pytest.mark.regression
    @allure.title("Viewer sees none of the user-management UI on the admin pages")
    def test_viewer_denied_admin_pages(self, viewer_session, user_factory, page):
        # The exact "access denied" wording differs between Grafana versions, so assert the outcome instead:
        # nothing that lets a user manage other users is rendered, and the page itself did load.
        other = user_factory("Viewer")  # a login that would be listed on the admin users page
        page.goto("/admin/users")
        page.wait_for_load_state("networkidle")
        expect(page.locator("body")).not_to_be_empty()
        expect(page.get_by_role("link", name=re.compile("new user", re.I))).to_have_count(0)
        expect(page.get_by_text(other.login)).to_have_count(0)
