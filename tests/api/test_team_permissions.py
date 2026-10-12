import time

import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.factories import unique_name


def _try_save(client, folder_uid: str, expected: int, timeout_s: int = 15) -> int:
    """Try to save a new dashboard as `client`, retrying briefly: Grafana caches permissions for a few seconds.
    Returns the last HTTP status (the caller asserts on it)."""
    builder = DashboardBuilder().in_folder(folder_uid)
    deadline = time.monotonic() + timeout_s
    while True:
        status = client.request("POST", "/api/dashboards/db", json=builder.build()).status_code
        if status == expected or time.monotonic() >= deadline:
            return status
        time.sleep(1)


@allure.epic("Grafana")
@allure.feature("Teams")
@pytest.mark.api
class TestTeamFolderPermissions:
    """An org Viewer cannot save dashboards. Granting their TEAM Edit on a folder must change that - in that folder only."""

    @pytest.fixture
    def setup(self, grafana_api, tracker, team_factory, user_factory):
        folder = grafana_api.create_folder(unique_name("AUTOMATION-teamperm"))
        tracker.register(grafana_api.delete_folder, folder["uid"])
        other = grafana_api.create_folder(unique_name("AUTOMATION-other"))
        tracker.register(grafana_api.delete_folder, other["uid"])
        return {"folder": folder["uid"], "other": other["uid"], "team": team_factory(),
                "viewer": user_factory("Viewer")}

    @pytest.mark.regression
    @allure.title("Baseline: a Viewer outside any team cannot save a dashboard")
    def test_baseline_viewer_cannot_save(self, setup):
        assert _try_save(setup["viewer"].client, setup["folder"], expected=403, timeout_s=1) == 403

    @pytest.mark.regression
    @allure.title("A team with Edit on a folder lets its Viewer members save dashboards there")
    def test_team_edit_grants_save(self, grafana_api, setup):
        grafana_api.add_team_member(setup["team"]["id"], setup["viewer"].id)
        grafana_api.set_folder_team_permission(setup["folder"], setup["team"]["id"], "Edit")
        assert _try_save(setup["viewer"].client, setup["folder"], expected=200) == 200

    @pytest.mark.regression
    @allure.title("The team's Edit permission applies to that folder only")
    def test_team_permission_is_scoped_to_folder(self, grafana_api, setup):
        grafana_api.add_team_member(setup["team"]["id"], setup["viewer"].id)
        grafana_api.set_folder_team_permission(setup["folder"], setup["team"]["id"], "Edit")
        assert _try_save(setup["viewer"].client, setup["folder"], expected=200) == 200
        assert _try_save(setup["viewer"].client, setup["other"], expected=200, timeout_s=3) == 403

    @pytest.mark.regression
    @allure.title("Removing the user from the team takes the access away again")
    def test_leaving_team_revokes_access(self, grafana_api, setup):
        grafana_api.add_team_member(setup["team"]["id"], setup["viewer"].id)
        grafana_api.set_folder_team_permission(setup["folder"], setup["team"]["id"], "Edit")
        assert _try_save(setup["viewer"].client, setup["folder"], expected=200) == 200

        grafana_api.remove_team_member(setup["team"]["id"], setup["viewer"].id)
        assert _try_save(setup["viewer"].client, setup["folder"], expected=403) == 403

    @pytest.mark.regression
    @allure.title("A team with only View on a folder does not let members save")
    def test_team_view_does_not_grant_save(self, grafana_api, setup):
        grafana_api.add_team_member(setup["team"]["id"], setup["viewer"].id)
        grafana_api.set_folder_team_permission(setup["folder"], setup["team"]["id"], "View")
        assert _try_save(setup["viewer"].client, setup["folder"], expected=200, timeout_s=3) == 403
