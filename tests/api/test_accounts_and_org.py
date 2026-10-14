import allure
import pytest

from utils.factories import unique_name


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@allure.epic("Grafana")
@allure.feature("Service accounts & organisation")
@pytest.mark.api
class TestServiceAccounts:
    @pytest.fixture
    def service_account(self, grafana_api, tracker):
        def _create(role: str) -> dict:
            created = grafana_api.request("POST", "/api/serviceaccounts",
                                          json={"name": unique_name(f"auto-sa-{role.lower()}"), "role": role})
            assert created.status_code == 201, created.text
            account = created.json()
            tracker.register(grafana_api.request, "DELETE", f"/api/serviceaccounts/{account['id']}")
            token = grafana_api.request("POST", f"/api/serviceaccounts/{account['id']}/tokens",
                                        json={"name": unique_name("auto-token")})
            assert token.status_code == 200, token.text
            return {"id": account["id"], "name": account["name"], "token": token.json()["key"]}

        return _create

    @pytest.mark.smoke
    @allure.title("A service account token authenticates API calls")
    def test_token_authenticates(self, grafana_api, service_account):
        sa = service_account("Viewer")
        resp = grafana_api.request("GET", "/api/user", authenticated=False, headers=_bearer(sa["token"]))
        assert resp.status_code == 200, resp.text
        assert resp.json()["login"].startswith("sa-")

    @pytest.mark.regression
    @allure.title("A Viewer service account cannot create dashboards; an Editor one can")
    def test_service_account_role_is_enforced(self, grafana_api, service_account, automation_folder, tracker):
        from utils.dashboard_builder import DashboardBuilder
        viewer, editor = service_account("Viewer"), service_account("Editor")

        denied = DashboardBuilder().in_folder(automation_folder["uid"])
        resp = grafana_api.request("POST", "/api/dashboards/db", authenticated=False,
                                   headers=_bearer(viewer["token"]), json=denied.build())
        assert resp.status_code == 403, resp.text

        allowed = DashboardBuilder().in_folder(automation_folder["uid"])
        resp = grafana_api.request("POST", "/api/dashboards/db", authenticated=False,
                                   headers=_bearer(editor["token"]), json=allowed.build())
        assert resp.status_code == 200, resp.text
        tracker.register(grafana_api.delete_dashboard, allowed.uid)

    @pytest.mark.regression
    @allure.title("Deleting a service account invalidates its token")
    def test_deleted_account_token_stops_working(self, grafana_api, service_account):
        sa = service_account("Viewer")
        assert grafana_api.request("GET", "/api/user", authenticated=False,
                                   headers=_bearer(sa["token"])).status_code == 200
        grafana_api.request("DELETE", f"/api/serviceaccounts/{sa['id']}")
        assert grafana_api.request("GET", "/api/user", authenticated=False,
                                   headers=_bearer(sa["token"])).status_code == 401


@allure.epic("Grafana")
@allure.feature("Service accounts & organisation")
@pytest.mark.api
class TestPasswordsAndPreferences:
    @pytest.mark.regression
    @allure.title("After an admin resets a password only the new one works")
    def test_password_reset(self, grafana_api, user_factory):
        user = user_factory("Viewer")
        new_password = unique_name("NewPw")
        resp = grafana_api.request("PUT", f"/api/admin/users/{user.id}/password", json={"password": new_password})
        assert resp.status_code == 200, resp.text

        assert user.client.request("GET", "/api/user").status_code == 401  # old password
        assert grafana_api.as_user(user.login, new_password).request("GET", "/api/user").status_code == 200

    @pytest.mark.regression
    @allure.title("Organisation preferences can be changed and are restored")
    def test_org_preferences(self, grafana_api, tracker):
        original = grafana_api.request("GET", "/api/org/preferences").json()
        tracker.register(lambda: grafana_api.request("PUT", "/api/org/preferences", json=original))

        new_theme = "light" if original.get("theme") != "light" else "dark"
        resp = grafana_api.request("PUT", "/api/org/preferences", json={**original, "theme": new_theme})
        assert resp.status_code == 200, resp.text
        assert grafana_api.request("GET", "/api/org/preferences").json()["theme"] == new_theme

    @pytest.mark.regression
    @allure.title("A Viewer cannot change organisation preferences")
    def test_viewer_cannot_change_org_preferences(self, user_factory):
        viewer = user_factory("Viewer")
        resp = viewer.client.request("PUT", "/api/org/preferences", json={"theme": "dark"})
        assert resp.status_code == 403, resp.text
