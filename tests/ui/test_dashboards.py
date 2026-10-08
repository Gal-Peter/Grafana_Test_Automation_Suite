import allure
import pytest
from playwright.sync_api import expect

from utils.dashboard_builder import DashboardBuilder
from utils.data_loader import load_cases


@allure.epic("Grafana")
@allure.feature("Dashboards")
class TestDashboards:
    @pytest.mark.parametrize("case", load_cases("dashboards_view", source="sqlite", json_columns=("panels",)))
    def test_dashboard_shows_title_and_panels(self, case, dashboard_factory, dashboard_page):
        allure.dynamic.title(f"Dashboard renders: {case['id']}")
        builder = DashboardBuilder().with_tags(*[t for t in case["tags"].split(",") if t])
        for panel in case["panels"]:
            builder.add_panel(panel["title"], panel["type"])
        dash = dashboard_factory(builder)

        dashboard_page.open_by_uid(dash.uid)

        expect(dashboard_page.title_breadcrumb(dash.title)).to_be_visible()
        for title in dash.panel_titles:
            expect(dashboard_page.panel(title).header).to_be_visible()

    @pytest.mark.smoke
    @allure.title("Dashboard can be found with the browse search")
    def test_search_finds_dashboard(self, dashboard_factory, dashboards_browse_page):
        dash = dashboard_factory()
        dashboards_browse_page.open().search(dash.title)
        expect(dashboards_browse_page.result(dash.title)).to_be_visible()

    @pytest.mark.regression
    @allure.title("Search with no match shows no result")
    def test_search_no_match(self, dashboards_browse_page):
        dashboards_browse_page.open().search("zzz-no-such-dashboard-zzz")
        expect(dashboards_browse_page.result("zzz-no-such-dashboard-zzz")).to_have_count(0)
