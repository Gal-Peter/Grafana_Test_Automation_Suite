import time

import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.factories import unique_name


def _wait_for(check, timeout_s: int = 15):
    deadline = time.monotonic() + timeout_s
    while True:
        result = check()
        if result or time.monotonic() >= deadline:
            return result
        time.sleep(0.5)


@allure.epic("Grafana")
@allure.feature("Folders (UI)")
class TestFoldersInUi:
    @pytest.mark.smoke
    @allure.title("A folder created in the UI exists and a dashboard can be moved into it")
    def test_create_folder_and_move_dashboard(self, grafana_api, automation_folder, dashboard_factory, tracker,
                                              folders_page):
        name = unique_name("AUTOMATION-ui-folder")
        dash = dashboard_factory()

        new_uid = folders_page.create_folder(name)
        tracker.register(grafana_api.delete_folder, new_uid)  # also removes whatever is inside it

        created = grafana_api.get_folder(new_uid)
        assert created.status_code == 200 and created.json()["title"] == name

        folders_page.open_folder(automation_folder["uid"]).move_dashboard(dash.uid, name)

        moved = _wait_for(lambda: grafana_api.get_dashboard(dash.uid).json()["meta"].get("folderUid") == new_uid)
        assert moved, "The dashboard is not in the new folder after moving it"

    @pytest.mark.regression
    @allure.title("Deleting a folder in the UI also deletes the dashboards inside it")
    def test_delete_folder(self, grafana_api, dashboard_factory, tracker, folders_page):
        folder = grafana_api.create_folder(unique_name("AUTOMATION-del-folder"))
        tracker.register(grafana_api.delete_folder, folder["uid"])
        dash = dashboard_factory(DashboardBuilder().in_folder(folder["uid"]))

        folders_page.delete_folder(folder["uid"], folder["title"])

        assert _wait_for(lambda: grafana_api.get_folder(folder["uid"]).status_code == 404), \
            "The folder still exists after deleting it"
        assert grafana_api.get_dashboard(dash.uid).status_code == 404, "The dashboard inside survived the folder"
