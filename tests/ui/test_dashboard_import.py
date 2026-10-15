import json
import time
from pathlib import Path

import allure
import pytest
from playwright.sync_api import expect

from utils.factories import unique_name

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "import_dashboard.json"


def _sample_dashboard() -> dict:
    """The sample file with a fresh uid and title, so runs never collide with each other or with leftovers."""
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    suffix = unique_name("").lstrip("-")
    data["uid"] = f"auto-imp-{suffix}"
    data["title"] = f"AUTOMATION-import-{suffix}"
    return data


def _wait_for_dashboard(api, uid: str, timeout_s: int = 15):
    deadline = time.monotonic() + timeout_s
    while True:
        resp = api.get_dashboard(uid)
        if resp.status_code == 200 or time.monotonic() >= deadline:
            return resp
        time.sleep(0.5)


@allure.epic("Grafana")
@allure.feature("Dashboards (UI)")
class TestDashboardImportInUi:
    @pytest.mark.smoke
    @allure.title("A dashboard can be imported from JSON")
    def test_import_from_json(self, grafana_api, tracker, import_page, dashboard_page):
        data = _sample_dashboard()
        tracker.register(grafana_api.delete_dashboard, data["uid"])

        import_page.import_json(json.dumps(data), data["uid"])

        resp = _wait_for_dashboard(grafana_api, data["uid"])
        assert resp.status_code == 200, "The imported dashboard does not exist"
        stored = resp.json()["dashboard"]
        assert stored["title"] == data["title"]
        assert sorted(stored["tags"]) == sorted(data["tags"])
        assert [p["title"] for p in stored["panels"]] == ["Imported panel"]

        dashboard_page.open_by_uid(data["uid"])
        expect(dashboard_page.title_breadcrumb(data["title"])).to_be_visible()
        expect(dashboard_page.panel("Imported panel").header).to_be_visible()

    @pytest.mark.regression
    @allure.title("Invalid JSON cannot be imported")
    def test_invalid_json_is_rejected(self, grafana_api, import_page, page):
        import_page.open()
        import_page.json_box.fill("{ this is not valid json")
        page.get_by_test_id("data-testid-load-dashboard").click()

        expect(import_page.import_button).to_have_count(0)  # never gets to the second step
        assert "/dashboard/import" in page.url
