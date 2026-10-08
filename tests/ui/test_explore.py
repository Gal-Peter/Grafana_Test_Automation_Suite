import allure
import pytest

from utils.data_loader import load_cases


@allure.epic("Grafana")
@allure.feature("Explore")
class TestExplore:
    @pytest.mark.regression
    @pytest.mark.parametrize("case", load_cases("explore_scenarios"))
    def test_run_query_succeeds(self, case, testdata_datasource, explore_page, settings):
        allure.dynamic.title(f"Explore query succeeds: {case['id']}")
        explore_page.open_with_query(testdata_datasource["uid"], settings.testdata_type, case["scenario"])
        response = explore_page.run_query()
        try:
            body = response.text()[:600]
        except Exception:
            body = "<response body unavailable>"
        assert response.status == 200, (
            f"/api/ds/query returned {response.status} for scenario '{case['scenario']}'. Grafana said: {body}")
