"""Facade over the Grafana HTTP API. Used for fast test setup/teardown and API tests."""
from __future__ import annotations

import time

import allure
import requests


class GrafanaApiError(Exception):
    pass


class GrafanaClient:
    def __init__(self, base_url: str, username: str, password: str, testdata_type: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.testdata_type = testdata_type
        self._timeout = timeout
        self._session = requests.Session()
        self._session.auth = (username, password)

    # -- low level -------------------------------------------------------
    def request(self, method: str, path: str, authenticated: bool = True, **kwargs) -> requests.Response:
        """Returns the raw response (no raising) so API tests can assert on any status."""
        url = f"{self.base_url}{path}"
        with allure.step(f"API {method} {path}"):
            if authenticated:
                return self._session.request(method, url, timeout=self._timeout, **kwargs)
            return requests.request(method, url, timeout=self._timeout, **kwargs)

    def _ok(self, response: requests.Response, action: str) -> dict:
        if not response.ok:
            raise GrafanaApiError(f"{action} failed: {response.status_code} {response.text[:300]}")
        return response.json() if response.content else {}

    # -- health ----------------------------------------------------------
    def health(self) -> dict:
        return self._ok(self.request("GET", "/api/health", authenticated=False), "health")

    def wait_until_healthy(self, timeout_s: int = 0) -> dict:
        """Poll /api/health; with timeout 0 it tries once. Handy for Docker/CI where Grafana boots slowly."""
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                return self.health()
            except (requests.RequestException, GrafanaApiError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)

    # -- folders ---------------------------------------------------------
    def create_folder(self, title: str, uid: str | None = None) -> dict:
        body = {"title": title, **({"uid": uid} if uid else {})}
        return self._ok(self.request("POST", "/api/folders", json=body), "create folder")

    def delete_folder(self, uid: str) -> None:
        self.request("DELETE", f"/api/folders/{uid}", params={"forceDeleteRules": "true"})

    # -- dashboards ------------------------------------------------------
    def create_dashboard(self, payload: dict) -> dict:
        return self._ok(self.request("POST", "/api/dashboards/db", json=payload), "create dashboard")

    def get_dashboard(self, uid: str) -> requests.Response:
        return self.request("GET", f"/api/dashboards/uid/{uid}")

    def delete_dashboard(self, uid: str) -> None:
        self.request("DELETE", f"/api/dashboards/uid/{uid}")

    def search(self, query: str = "", **params) -> list[dict]:
        return self._ok(self.request("GET", "/api/search", params={"query": query, **params}), "search")

    def get_folder(self, uid: str) -> requests.Response:
        return self.request("GET", f"/api/folders/{uid}")

    def rename_folder(self, uid: str, title: str, version: int) -> dict:
        body = {"title": title, "version": version, "overwrite": True}
        return self._ok(self.request("PUT", f"/api/folders/{uid}", json=body), "rename folder")

    # -- users & roles (admin API) -----------------------------------------
    def create_user(self, login: str, password: str) -> dict:
        body = {"name": login, "email": f"{login}@example.com", "login": login, "password": password}
        return self._ok(self.request("POST", "/api/admin/users", json=body), "create user")

    def set_org_role(self, user_id: int, role: str) -> None:
        self._ok(self.request("PATCH", f"/api/org/users/{user_id}", json={"role": role}), f"set role {role}")

    def delete_user(self, user_id: int) -> None:
        self.request("DELETE", f"/api/admin/users/{user_id}")

    def as_user(self, login: str, password: str) -> "GrafanaClient":
        """A second client that authenticates as another user (to test what that role may do)."""
        return GrafanaClient(self.base_url, login, password, self.testdata_type, self._timeout)

    # -- teams -------------------------------------------------------------
    def create_team(self, name: str) -> dict:
        return self._ok(self.request("POST", "/api/teams", json={"name": name, "email": f"{name}@example.com"}),
                        "create team")

    def get_team(self, team_id: int) -> requests.Response:
        return self.request("GET", f"/api/teams/{team_id}")

    def delete_team(self, team_id: int) -> None:
        self.request("DELETE", f"/api/teams/{team_id}")

    def search_teams(self, name: str) -> list[dict]:
        return self._ok(self.request("GET", "/api/teams/search", params={"name": name}), "search teams")["teams"]

    def add_team_member(self, team_id: int, user_id: int) -> None:
        self._ok(self.request("POST", f"/api/teams/{team_id}/members", json={"userId": user_id}), "add team member")

    def remove_team_member(self, team_id: int, user_id: int) -> None:
        self._ok(self.request("DELETE", f"/api/teams/{team_id}/members/{user_id}"), "remove team member")

    def team_members(self, team_id: int) -> list[dict]:
        return self._ok(self.request("GET", f"/api/teams/{team_id}/members"), "list team members")

    def set_folder_team_permission(self, folder_uid: str, team_id: int, permission: str) -> None:
        """permission: 'View' | 'Edit' | 'Admin'. An empty string removes the team's permission."""
        self._ok(self.request("POST", f"/api/access-control/folders/{folder_uid}/teams/{team_id}",
                              json={"permission": permission}), f"set folder permission {permission or 'none'}")

    # -- data sources ----------------------------------------------------
    def create_testdata_datasource(self, name: str) -> dict:
        body = {"name": name, "type": self.testdata_type, "access": "proxy"}
        result = self._ok(self.request("POST", "/api/datasources", json=body), "create datasource")
        return result["datasource"]

    def get_datasource(self, uid: str) -> requests.Response:
        return self.request("GET", f"/api/datasources/uid/{uid}")

    def delete_datasource(self, uid: str) -> None:
        self.request("DELETE", f"/api/datasources/uid/{uid}")
