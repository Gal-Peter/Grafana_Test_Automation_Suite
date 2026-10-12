import allure
import pytest

from utils.factories import unique_name


@allure.epic("Grafana")
@allure.feature("Teams")
@pytest.mark.api
class TestTeams:
    @pytest.mark.smoke
    @allure.title("Team lifecycle: create, find, delete")
    def test_team_lifecycle(self, grafana_api, tracker):
        name = unique_name("auto-team")
        team = grafana_api.create_team(name)
        tracker.register(grafana_api.delete_team, team["teamId"])

        assert grafana_api.get_team(team["teamId"]).status_code == 200
        assert name in [t["name"] for t in grafana_api.search_teams(name)]

        grafana_api.delete_team(team["teamId"])
        assert grafana_api.get_team(team["teamId"]).status_code == 404

    @pytest.mark.regression
    @allure.title("A user can be added to and removed from a team")
    def test_membership(self, grafana_api, team_factory, user_factory):
        team = team_factory()
        user = user_factory("Viewer")

        grafana_api.add_team_member(team["id"], user.id)
        assert user.login in [m["login"] for m in grafana_api.team_members(team["id"])]

        grafana_api.remove_team_member(team["id"], user.id)
        assert user.login not in [m["login"] for m in grafana_api.team_members(team["id"])]

    @pytest.mark.regression
    @allure.title("Team names must be unique")
    def test_duplicate_name_rejected(self, grafana_api, team_factory):
        team = team_factory()
        resp = grafana_api.request("POST", "/api/teams", json={"name": team["name"]})
        assert resp.status_code in (400, 409), resp.text

    @pytest.mark.regression
    @allure.title("A Viewer cannot create a team")
    def test_viewer_cannot_create_team(self, user_factory):
        viewer = user_factory("Viewer")
        resp = viewer.client.request("POST", "/api/teams", json={"name": unique_name("nope")})
        assert resp.status_code == 403, resp.text

    @pytest.mark.regression
    @allure.title("Deleting a team removes it from the search")
    def test_deleted_team_not_found(self, grafana_api, team_factory):
        team = team_factory()
        grafana_api.delete_team(team["id"])
        assert team["name"] not in [t["name"] for t in grafana_api.search_teams(team["name"])]
