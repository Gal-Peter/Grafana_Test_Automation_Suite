import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.data_loader import load_cases


@allure.epic("Grafana")
@allure.feature("Mobile web - Dashboards")
@pytest.mark.mobile
class TestMobileDashboards:
    @pytest.mark.regression
    @pytest.mark.parametrize("case", load_cases("dashboards_view", source="sqlite", json_columns=("panels",)))
    def test_dashboard_renders_and_fits_screen(self, case, dashboard_factory, mobile_dashboard_screen):
        allure.dynamic.title(f"Mobile: dashboard renders - {case['id']}")
        builder = DashboardBuilder()
        for panel in case["panels"]:
            builder.add_panel(panel["title"], panel["type"])
        dash = dashboard_factory(builder)

        mobile_dashboard_screen.open_by_uid(dash.uid)

        mobile_dashboard_screen.wait_text(dash.title)
        for title in dash.panel_titles:
            assert mobile_dashboard_screen.has_text(title, timeout=10), f"Panel '{title}' not visible"
        assert not mobile_dashboard_screen.has_horizontal_overflow(), "Page scrolls horizontally on mobile"
