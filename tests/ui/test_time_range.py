import re

import allure
import pytest
from playwright.sync_api import expect


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
class TestTimeRangeInUi:
    @pytest.mark.smoke
    @allure.title("The time range picker changes the range and it shows in the URL")
    def test_pick_time_ranges(self, dashboard_factory, dashboard_page, page):
        dash = dashboard_factory()
        dashboard_page.open_by_uid(dash.uid)

        dashboard_page.set_time_range("Last 1 hour")
        expect(page).to_have_url(re.compile(r"from=now-1h&to=now"))
        expect(dashboard_page.time_picker_button).to_contain_text("Last 1 hour")

        dashboard_page.set_time_range("Last 24 hours")
        expect(page).to_have_url(re.compile(r"from=now-24h&to=now"))
        expect(dashboard_page.time_picker_button).to_contain_text("Last 24 hours")

    @pytest.mark.regression
    @allure.title("The chosen time range survives a page reload")
    def test_time_range_survives_reload(self, dashboard_factory, dashboard_page, page):
        dash = dashboard_factory()
        dashboard_page.open_by_uid(dash.uid)
        dashboard_page.set_time_range("Last 12 hours")
        expect(page).to_have_url(re.compile(r"from=now-12h&to=now"))

        page.reload()

        expect(page).to_have_url(re.compile(r"from=now-12h&to=now"))
        expect(dashboard_page.time_picker_button).to_contain_text("Last 12 hours")
