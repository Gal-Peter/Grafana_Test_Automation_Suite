import time

import allure
import pytest
from playwright.sync_api import expect

from utils.factories import alert_rule_payload, unique_name

PROVISION = "/api/v1/provisioning"
KEEP_EDITABLE = {"X-Disable-Provenance": "true"}


def _wait_for_rule(api, title: str, present: bool = True, timeout_s: int = 15) -> list[dict]:
    deadline = time.monotonic() + timeout_s
    while True:
        rules = api.find_alert_rules(title)
        if bool(rules) == present or time.monotonic() >= deadline:
            return rules
        time.sleep(0.5)


@pytest.fixture
def contact_point(grafana_api, tracker) -> str:
    name = unique_name("auto-contact")
    body = {"name": name, "type": "email", "settings": {"addresses": "qa@example.com"}}
    resp = grafana_api.request("POST", f"{PROVISION}/contact-points", json=body, headers=KEEP_EDITABLE)
    assert resp.status_code in (200, 201, 202), resp.text
    uid = resp.json()["uid"]
    tracker.register(grafana_api.request, "DELETE", f"{PROVISION}/contact-points/{uid}")
    return name


@allure.epic("Grafana")
@allure.feature("Alerting (UI)")
class TestAlertRulesInUi:
    @pytest.mark.smoke
    @allure.title("An alert rule created in the UI is saved with the chosen settings")
    def test_create_rule(self, grafana_api, automation_folder, testdata_datasource, tracker, contact_point,
                         alert_rule_page):
        title = unique_name("AUTOMATION-ui-rule")
        group = unique_name("auto-group")
        tracker.register(grafana_api.delete_alert_rules_titled, title)  # runs even if the test fails half-way

        alert_rule_page.open_new_from_ui()
        alert_rule_page.fill_rule(title, 20, automation_folder["title"], group, contact_point, "created by automation",
                                  datasource=testdata_datasource["name"])
        alert_rule_page.save()

        rules = _wait_for_rule(grafana_api, title)
        assert len(rules) == 1, f"Expected one rule titled {title}, found {len(rules)}"
        rule = rules[0]
        assert rule["folderUID"] == automation_folder["uid"]
        assert rule["ruleGroup"] == group
        assert rule["annotations"].get("summary") == "created by automation"
        assert rule.get("notification_settings", {}).get("receiver") == contact_point, rule
        thresholds = [d["model"]["conditions"][0]["evaluator"]["params"] for d in rule["data"]
                      if d.get("model", {}).get("conditions")]
        assert [20] in thresholds, f"Threshold 20 not found in the saved rule: {rule['data']}"

        alert_rule_page.open_filtered(title)
        expect(alert_rule_page.reveal_rule(title, automation_folder["title"], group)).to_be_visible()

    @pytest.mark.regression
    @allure.title("An alert rule can be deleted from the rule list")
    def test_delete_rule(self, grafana_api, automation_folder, testdata_datasource, tracker, alert_rule_page):
        title = unique_name("AUTOMATION-del-rule")
        payload = alert_rule_payload(automation_folder["uid"], testdata_datasource, grafana_api.testdata_type, title)
        created = grafana_api.request("POST", f"{PROVISION}/alert-rules", json=payload, headers=KEEP_EDITABLE)
        assert created.status_code in (200, 201), created.text
        tracker.register(grafana_api.delete_alert_rules_titled, title)

        alert_rule_page.delete_from_list(title, automation_folder["title"], payload["ruleGroup"])

        assert not _wait_for_rule(grafana_api, title, present=False), "The rule still exists after deleting it"
