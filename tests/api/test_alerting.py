import allure
import pytest

from utils.factories import alert_rule_payload as _rule_payload
from utils.factories import unique_name

PROVISION = "/api/v1/provisioning"
KEEP_EDITABLE = {"X-Disable-Provenance": "true"}  # without it Grafana locks API-created items in the UI


@allure.epic("Grafana")
@allure.feature("Alerting")
@pytest.mark.api
class TestAlertRules:
    @pytest.fixture
    def rule(self, grafana_api, automation_folder, testdata_datasource, tracker):
        payload = _rule_payload(automation_folder["uid"], testdata_datasource, grafana_api.testdata_type)
        resp = grafana_api.request("POST", f"{PROVISION}/alert-rules", json=payload, headers=KEEP_EDITABLE)
        assert resp.status_code in (200, 201), resp.text
        created = resp.json()
        tracker.register(grafana_api.request, "DELETE", f"{PROVISION}/alert-rules/{created['uid']}")
        return created

    @pytest.mark.smoke
    @allure.title("Alert rule lifecycle: create, read, delete")
    def test_rule_lifecycle(self, grafana_api, rule):
        got = grafana_api.request("GET", f"{PROVISION}/alert-rules/{rule['uid']}")
        assert got.status_code == 200 and got.json()["title"] == rule["title"]

        deleted = grafana_api.request("DELETE", f"{PROVISION}/alert-rules/{rule['uid']}")
        assert deleted.status_code in (200, 204), deleted.text
        assert grafana_api.request("GET", f"{PROVISION}/alert-rules/{rule['uid']}").status_code == 404

    @pytest.mark.regression
    @allure.title("A rule can be updated and keeps its uid")
    def test_rule_update(self, grafana_api, rule):
        changed = {**rule, "title": unique_name("auto-renamed")}
        resp = grafana_api.request("PUT", f"{PROVISION}/alert-rules/{rule['uid']}", json=changed,
                                   headers=KEEP_EDITABLE)
        assert resp.status_code == 200, resp.text
        assert grafana_api.request("GET", f"{PROVISION}/alert-rules/{rule['uid']}").json()["title"] == changed["title"]

    @pytest.mark.regression
    @allure.title("A rule without a title is rejected")
    def test_rule_requires_title(self, grafana_api, automation_folder, testdata_datasource):
        payload = _rule_payload(automation_folder["uid"], testdata_datasource, grafana_api.testdata_type, title="")
        resp = grafana_api.request("POST", f"{PROVISION}/alert-rules", json=payload, headers=KEEP_EDITABLE)
        assert resp.status_code == 400, resp.text

    @pytest.mark.regression
    @allure.title("A Viewer cannot create alert rules")
    def test_viewer_cannot_create_rule(self, grafana_api, user_factory, automation_folder, testdata_datasource):
        viewer = user_factory("Viewer")
        payload = _rule_payload(automation_folder["uid"], testdata_datasource, grafana_api.testdata_type)
        resp = viewer.client.request("POST", f"{PROVISION}/alert-rules", json=payload)
        assert resp.status_code == 403, resp.text


@allure.epic("Grafana")
@allure.feature("Alerting")
@pytest.mark.api
class TestContactPointsAndPolicies:
    @pytest.mark.smoke
    @allure.title("Contact point lifecycle: create, list, delete")
    def test_contact_point_lifecycle(self, grafana_api, tracker):
        name = unique_name("auto-contact")
        body = {"name": name, "type": "email", "settings": {"addresses": "qa@example.com"}}
        created = grafana_api.request("POST", f"{PROVISION}/contact-points", json=body, headers=KEEP_EDITABLE)
        assert created.status_code in (200, 201, 202), created.text
        uid = created.json()["uid"]
        tracker.register(grafana_api.request, "DELETE", f"{PROVISION}/contact-points/{uid}")

        listed = grafana_api.request("GET", f"{PROVISION}/contact-points", params={"name": name})
        assert name in [c["name"] for c in listed.json()]

        deleted = grafana_api.request("DELETE", f"{PROVISION}/contact-points/{uid}")
        assert deleted.status_code in (200, 202, 204), deleted.text
        after = grafana_api.request("GET", f"{PROVISION}/contact-points", params={"name": name})
        assert name not in [c["name"] for c in after.json()]

    @pytest.mark.regression
    @allure.title("The default notification policy exists and has a receiver")
    def test_default_policy(self, grafana_api):
        resp = grafana_api.request("GET", f"{PROVISION}/policies")
        assert resp.status_code == 200, resp.text
        assert resp.json().get("receiver")

    @pytest.mark.regression
    @allure.title("A Viewer cannot create contact points")
    def test_viewer_cannot_create_contact_point(self, user_factory):
        viewer = user_factory("Viewer")
        body = {"name": unique_name("nope"), "type": "email", "settings": {"addresses": "qa@example.com"}}
        resp = viewer.client.request("POST", f"{PROVISION}/contact-points", json=body)
        assert resp.status_code == 403, resp.text
