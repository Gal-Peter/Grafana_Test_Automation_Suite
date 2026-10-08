import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.data_loader import load_cases


@allure.epic("Grafana")
@allure.feature("Dashboard API")
@pytest.mark.api
class TestDashboardApi:
    @pytest.mark.smoke
    @allure.title("Dashboard lifecycle: create, read, delete")
    def test_lifecycle(self, grafana_api, automation_folder, tracker):
        builder = DashboardBuilder().in_folder(automation_folder["uid"]).add_panel("P1")
        created = grafana_api.create_dashboard(builder.build())
        tracker.register(grafana_api.delete_dashboard, builder.uid)
        assert created["uid"] == builder.uid

        got = grafana_api.get_dashboard(builder.uid)
        assert got.status_code == 200
        assert got.json()["dashboard"]["title"] == builder.title

        grafana_api.delete_dashboard(builder.uid)
        assert grafana_api.get_dashboard(builder.uid).status_code == 404

    @pytest.mark.regression
    @pytest.mark.parametrize("case", load_cases("api_negative_cases", source="sqlite", json_columns=("body",)))
    def test_negative_cases(self, case, grafana_api):
        allure.dynamic.title(f"API negative: {case['id']}")
        kwargs = {"json": case["body"]} if case["body"] is not None else {}
        resp = grafana_api.request(case["method"], case["path"],
                                   authenticated=bool(case["authenticated"]), **kwargs)
        assert resp.status_code == case["expected_status"], resp.text
