import time

import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.factories import unique_name


def _versions(resp) -> list:
    data = resp.json()
    return data.get("versions", data) if isinstance(data, dict) else data


@allure.epic("Grafana")
@allure.feature("Dashboard features")
@pytest.mark.api
class TestImportExport:
    @pytest.mark.smoke
    @allure.title("A dashboard exported as JSON can be imported again")
    def test_export_then_import(self, grafana_api, dashboard_factory, automation_folder, tracker):
        original = dashboard_factory()
        exported = grafana_api.get_dashboard(original.uid).json()["dashboard"]  # export = the stored JSON

        exported.update({"uid": unique_name("imp"), "title": unique_name("AUTOMATION-imported"), "id": None})
        resp = grafana_api.request("POST", "/api/dashboards/import", json={
            "dashboard": exported, "overwrite": False, "folderUid": automation_folder["uid"], "inputs": []})
        assert resp.status_code == 200, resp.text
        tracker.register(grafana_api.delete_dashboard, exported["uid"])

        got = grafana_api.get_dashboard(exported["uid"]).json()
        assert got["dashboard"]["title"] == exported["title"]
        assert [p["title"] for p in got["dashboard"]["panels"]] == original.panel_titles

    @pytest.mark.regression
    @allure.title("Importing JSON without a title is rejected")
    def test_import_requires_title(self, grafana_api, automation_folder):
        resp = grafana_api.request("POST", "/api/dashboards/import", json={
            "dashboard": {"title": "", "panels": []}, "overwrite": False,
            "folderUid": automation_folder["uid"], "inputs": []})
        assert resp.status_code in (400, 412), resp.text


@allure.epic("Grafana")
@allure.feature("Dashboard features")
@pytest.mark.api
class TestDashboardOrganisation:
    @pytest.mark.regression
    @allure.title("A dashboard can be moved to another folder")
    def test_move_between_folders(self, grafana_api, dashboard_factory, tracker):
        target = grafana_api.create_folder(unique_name("AUTOMATION-target"))
        tracker.register(grafana_api.delete_folder, target["uid"])
        dash = dashboard_factory()
        body = grafana_api.get_dashboard(dash.uid).json()["dashboard"]

        grafana_api.create_dashboard({"dashboard": body, "folderUid": target["uid"], "overwrite": True})
        assert grafana_api.get_dashboard(dash.uid).json()["meta"]["folderUid"] == target["uid"]

    @pytest.mark.regression
    @allure.title("A dashboard can be starred and unstarred")
    def test_star_and_unstar(self, grafana_api, dashboard_factory):
        dash = dashboard_factory()
        assert grafana_api.request("POST", f"/api/user/stars/dashboard/uid/{dash.uid}").status_code == 200
        assert dash.uid in grafana_api.request("GET", "/api/user/stars").text

        assert grafana_api.request("DELETE", f"/api/user/stars/dashboard/uid/{dash.uid}").status_code == 200
        assert dash.uid not in grafana_api.request("GET", "/api/user/stars").text

    @pytest.mark.regression
    @allure.title("Every save adds a version to the dashboard history")
    def test_version_history(self, grafana_api, dashboard_factory, automation_folder):
        dash = dashboard_factory()
        for n in range(2):
            body = grafana_api.get_dashboard(dash.uid).json()["dashboard"]
            body["title"] = f"{dash.title}-v{n}"
            grafana_api.create_dashboard({"dashboard": body, "folderUid": automation_folder["uid"], "overwrite": True})
        resp = grafana_api.request("GET", f"/api/dashboards/uid/{dash.uid}/versions")
        assert resp.status_code == 200, resp.text
        assert len(_versions(resp)) >= 3


@allure.epic("Grafana")
@allure.feature("Dashboard features")
@pytest.mark.api
class TestVariablesAndTimeRange:
    @pytest.mark.regression
    @allure.title("Dashboard variables and the saved time range are stored")
    def test_templating_and_time_range_persist(self, grafana_api, automation_folder, tracker):
        builder = DashboardBuilder().in_folder(automation_folder["uid"]).add_panel("Panel")
        payload = builder.build()
        payload["dashboard"]["time"] = {"from": "now-1h", "to": "now"}
        payload["dashboard"]["templating"] = {"list": [{
            "name": "env", "label": "Environment", "type": "custom", "query": "dev,staging,prod",
            "current": {"text": "staging", "value": "staging"},
            "options": [{"text": v, "value": v, "selected": v == "staging"} for v in ("dev", "staging", "prod")]}]}
        grafana_api.create_dashboard(payload)
        tracker.register(grafana_api.delete_dashboard, builder.uid)

        stored = grafana_api.get_dashboard(builder.uid).json()["dashboard"]
        assert stored["time"]["from"] == "now-1h"
        variable = stored["templating"]["list"][0]
        assert variable["name"] == "env" and variable["current"]["value"] == "staging"
        assert [o["value"] for o in variable["options"]] == ["dev", "staging", "prod"]


@allure.epic("Grafana")
@allure.feature("Dashboard features")
@pytest.mark.api
class TestAnnotations:
    @pytest.mark.regression
    @allure.title("Annotation lifecycle: create, find, delete")
    def test_annotation_lifecycle(self, grafana_api, dashboard_factory):
        dash = dashboard_factory()
        text = unique_name("deploy-marker")
        created = grafana_api.request("POST", "/api/annotations", json={
            "dashboardUID": dash.uid, "time": int(time.time() * 1000), "text": text, "tags": ["automation"]})
        assert created.status_code == 200, created.text
        annotation_id = created.json()["id"]

        found = grafana_api.request("GET", "/api/annotations", params={"dashboardUID": dash.uid})
        assert text in [a["text"] for a in found.json()]

        assert grafana_api.request("DELETE", f"/api/annotations/{annotation_id}").status_code == 200
        found = grafana_api.request("GET", "/api/annotations", params={"dashboardUID": dash.uid})
        assert text not in [a["text"] for a in found.json()]
