"""Creating and deleting alert rules in the UI. Locators come from a Playwright codegen recording on Grafana 13.2.2."""
from __future__ import annotations

import re
from urllib.parse import quote

from playwright.sync_api import Locator

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class AlertRulePage(BasePage):
    path = "/alerting/list"

    def _tid(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    @step("Start a new alert rule from the Alert rules page")
    def open_new_from_ui(self):
        self.page.goto(self.path)
        self._click(self._tid("data-testid rule-list new-alert-rule-link"), "'New alert rule'")
        self._tid("data-testid alert-rule name-field").wait_for(state="visible")
        return self

    @step("Fill in the rule: {name}, threshold {threshold}")
    def fill_rule(self, name: str, threshold: int, folder: str, group: str, contact_point: str, summary: str,
                  datasource: str | None = None):
        self._tid("data-testid alert-rule name-field").fill(name)
        if datasource:
            self._choose_datasource(datasource)
        self._tid("data-testid alert-rule threshold-input").fill(str(threshold))

        self._click(self._tid("data-testid folder-picker-trigger-button"), "the folder picker")
        self._click(self.page.get_by_role("treeitem", name=folder), f"folder '{folder}' in the picker")

        self._click(self._tid("data-testid alert-rule new-evaluation-group-button"), "'New evaluation group'")
        self._tid("data-testid alert-rule new-evaluation-group-name").fill(group)
        self._click(self._tid("data-testid alert-rule new-evaluation-group-create-button"), "'Create' evaluation group")

        self._click(self._tid("data-testid alert-rule contact-point-input"), "the contact point picker")
        option = self.page.get_by_role("option", name=contact_point).or_(
            self.page.get_by_text(contact_point, exact=True)).first
        self._click(option, f"contact point '{contact_point}'")

        self._tid("annotation-value-0").fill(summary)
        return self

    def _choose_datasource(self, name: str):
        """A fresh Grafana (CI, Docker) has no default data source, so the query needs one picked explicitly."""
        self._click(self._tid("data-testid Data source picker select container"), "the query data source picker")
        option = self.page.get_by_role("option", name=name).or_(self.page.get_by_text(name, exact=True)).first
        self._click(option, f"data source '{name}' in the picker")

    @step("Save the rule")
    def save(self):
        self._click(self._tid("data-testid alert-rule save-rule-button"), "'Save rule and exit'")
        try:
            self.page.wait_for_url(lambda url: "/alerting/new" not in url, timeout=15000)
        except Exception as exc:
            raise AssertionError(f"The rule was not saved (still on the form).\n{self._where_are_we()}") from exc
        return self

    def rule_row(self, name: str) -> Locator:
        return self.page.get_by_role("treeitem", name=re.compile(re.escape(name)))

    def reveal_rule(self, name: str, *containers: str):
        """Wait for the rule to show in the list. Folders/groups may be collapsed: expand them (outermost first)
        and, if the rule still is not there, fail with the page state so the cause is visible."""
        row = self.rule_row(name).first
        if self._appears(row, 6000):
            return row
        for container in containers:
            parent = self.page.get_by_role("treeitem").filter(has_text=container).first
            toggle = parent.get_by_label("Expand")
            if toggle.count():
                toggle.first.click()
                if self._appears(row, 4000):
                    return row
        raise AssertionError(f"Rule '{name}' is not visible in the rule list.\n{self._where_are_we()}")

    @staticmethod
    def _appears(locator: Locator, timeout_ms: int) -> bool:
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    @step("Delete the rule {name} from the list")
    def open_filtered(self, name: str):
        """The list can be long (every folder and group): filter it by the rule name through the URL."""
        self.page.goto(f"{self.path}?search={quote(name)}")
        return self

    def delete_from_list(self, name: str, *containers: str):
        self.open_filtered(name)
        row = self.reveal_rule(name, *containers)
        self._click(row.get_by_label("More"), f"the 'More' menu of rule '{name}'", timeout_ms=10000)
        self._click(self.page.get_by_role("menuitem", name="Delete"), "'Delete' in the menu")
        self._click(self._tid("data-testid Confirm Modal Danger Button"), "the delete confirmation button")
        return self
