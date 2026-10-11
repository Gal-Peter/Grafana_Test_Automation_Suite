import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.factories import unique_name


@allure.epic("Grafana")
@allure.feature("Folders, data sources & dashboard updates")
@pytest.mark.api
class TestFolders:
    @pytest.mark.smoke
    @allure.title("Folder lifecycle: create, rename, delete")
    def test_folder_lifecycle(self, grafana_api, tracker):
        folder = grafana_api.create_folder(unique_name("AUTOMATION-folder"))
        tracker.register(grafana_api.delete_folder, folder["uid"])

        new_title = unique_name("AUTOMATION-renamed")
        grafana_api.rename_folder(folder["uid"], new_title, folder.get("version", 1))
        assert grafana_api.get_folder(folder["uid"]).json()["title"] == new_title

        grafana_api.delete_folder(folder["uid"])
        assert grafana_api.get_folder(folder["uid"]).status_code == 404

    @pytest.mark.regression
    @allure.title("Deleting a folder also deletes the dashboards inside it")
    def test_delete_folder_removes_dashboards(self, grafana_api, tracker):
        folder = grafana_api.create_folder(unique_name("AUTOMATION-cascade"))
        tracker.register(grafana_api.delete_folder, folder["uid"])
        builder = DashboardBuilder().in_folder(folder["uid"])
        grafana_api.create_dashboard(builder.build())
        assert grafana_api.get_dashboard(builder.uid).status_code == 200

        grafana_api.delete_folder(folder["uid"])
        assert grafana_api.get_dashboard(builder.uid).status_code == 404


@allure.epic("Grafana")
@allure.feature("Folders, data sources & dashboard updates")
@pytest.mark.api
class TestDashboardUpdates:
    @pytest.mark.regression
    @allure.title("Updating a dashboard changes its title and bumps the version")
    def test_update_bumps_version(self, grafana_api, dashboard_factory, automation_folder):
        dash = dashboard_factory()
        current = grafana_api.get_dashboard(dash.uid).json()["dashboard"]
        old_version = current["version"]

        current["title"] = unique_name("AUTOMATION-updated")
        grafana_api.create_dashboard({"dashboard": current, "folderUid": automation_folder["uid"], "overwrite": True})

        updated = grafana_api.get_dashboard(dash.uid).json()["dashboard"]
        assert updated["title"] == current["title"]
        assert updated["version"] > old_version

    @pytest.mark.regression
    @allure.title("Search by tag returns only dashboards with that tag")
    def test_search_by_tag(self, grafana_api, dashboard_factory):
        tag = unique_name("tag")
        tagged = dashboard_factory(DashboardBuilder().with_tags(tag))
        other = dashboard_factory()
        uids = {hit["uid"] for hit in grafana_api.search(tag=tag)}
        assert tagged.uid in uids
        assert other.uid not in uids


@allure.epic("Grafana")
@allure.feature("Folders, data sources & dashboard updates")
@pytest.mark.api
class TestDataSources:
    @pytest.mark.smoke
    @allure.title("Data source lifecycle: create, read, delete")
    def test_datasource_lifecycle(self, grafana_api, tracker):
        ds = grafana_api.create_testdata_datasource(unique_name("auto-testdata"))
        tracker.register(grafana_api.delete_datasource, ds["uid"])
        got = grafana_api.get_datasource(ds["uid"])
        assert got.status_code == 200 and got.json()["name"] == ds["name"]

        grafana_api.delete_datasource(ds["uid"])
        assert grafana_api.get_datasource(ds["uid"]).status_code == 404

    @pytest.mark.regression
    @allure.title("Data source names must be unique")
    def test_duplicate_name_rejected(self, grafana_api, testdata_datasource):
        resp = grafana_api.request("POST", "/api/datasources", json={
            "name": testdata_datasource["name"], "type": grafana_api.testdata_type, "access": "proxy"})
        assert resp.status_code in (409, 400), resp.text
