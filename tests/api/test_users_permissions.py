import allure
import pytest

from utils.dashboard_builder import DashboardBuilder
from utils.data_loader import load_cases
from utils.factories import unique_name


@allure.epic("Grafana")
@allure.feature("Users & permissions")
@pytest.mark.api
class TestRolePermissions:
    """Role matrix (CSV-driven): what may a Viewer / Editor / org Admin do?

    Org Admin is NOT a server admin, so server-wide endpoints stay forbidden even for them.
    """

    @pytest.mark.regression
    @pytest.mark.parametrize("case", load_cases("role_permissions"))
    def test_role_matrix(self, case, user_factory, dashboard_factory, grafana_api, automation_folder, tracker):
        allure.dynamic.title(f"{case['role']} -> {case['action']} = {case['expected_status']}")
        user = user_factory(case["role"])
        existing = dashboard_factory()  # created by the admin, inside the automation folder

        action = case["action"]
        if action == "view_dashboard":
            resp = user.client.get_dashboard(existing.uid)
        elif action == "create_dashboard":
            builder = DashboardBuilder().in_folder(automation_folder["uid"])
            resp = user.client.request("POST", "/api/dashboards/db", json=builder.build())
            if resp.ok:
                tracker.register(grafana_api.delete_dashboard, builder.uid)
        elif action == "create_datasource":
            resp = user.client.request("POST", "/api/datasources", json={
                "name": unique_name("auto-ds"), "type": grafana_api.testdata_type, "access": "proxy"})
            if resp.ok:
                tracker.register(grafana_api.delete_datasource, resp.json()["datasource"]["uid"])
        elif action == "server_stats":
            resp = user.client.request("GET", "/api/admin/stats")
        else:
            pytest.fail(f"Unknown action in role_permissions.csv: {action}")

        assert resp.status_code == int(case["expected_status"]), resp.text

    @pytest.mark.smoke
    @allure.title("A newly created user can authenticate and has the requested role")
    def test_new_user_has_role(self, user_factory):
        user = user_factory("Editor")
        resp = user.client.request("GET", "/api/user")
        assert resp.status_code == 200, resp.text
        assert resp.json()["login"] == user.login
        orgs = user.client.request("GET", "/api/user/orgs").json()
        assert orgs and orgs[0]["role"] == "Editor"

    @pytest.mark.regression
    @allure.title("A deleted user can no longer authenticate")
    def test_deleted_user_is_locked_out(self, user_factory, grafana_api):
        user = user_factory("Viewer")
        assert user.client.request("GET", "/api/user").status_code == 200
        grafana_api.delete_user(user.id)
        assert user.client.request("GET", "/api/user").status_code == 401
