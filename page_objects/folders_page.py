"""Folders in the Dashboards browser: create, move dashboards into one, delete. Locators come from a codegen recording."""
from __future__ import annotations

import re
from urllib.parse import quote

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class FoldersPage(BasePage):
    path = "/dashboards"

    def _tick(self, box, what: str):
        """Grafana draws a styled <span> over the real checkbox, which 'intercepts pointer events':
        click through it (force) and then confirm the box really is ticked."""
        try:
            box.check(force=True, timeout=10000)
        except Exception as exc:
            raise AssertionError(f"Could not tick the checkbox of {what}.\n{self._where_are_we()}") from exc

    def _select_by_uid(self, uid: str):
        """Inside a folder the rows carry a test id built from the item's uid."""
        self._tick(self.page.get_by_test_id(f"data-testid {uid} checkbox"), f"'{uid}'")

    def _select_by_name(self, name: str):
        """In search results the rows have no test id: find the row by its text."""
        row = self.page.get_by_role("row").filter(has_text=name)
        self._tick(row.get_by_role("checkbox").first, f"the row '{name}'")

    @step("Create the folder '{name}' in the UI")
    def create_folder(self, name: str) -> str:
        """Returns the new folder's uid (read from the URL Grafana opens after creating it)."""
        self.page.goto(self.path)
        self._click(self.page.get_by_test_id("data-testid CreateNewButton New button"), "the 'New' button")
        self._click(self.page.get_by_role("menuitem", name="New folder"), "'New folder'")
        self.page.get_by_test_id("data-testid new-folder-name-input").fill(name)
        self._click(self.page.get_by_role("button", name="Create", exact=True), "'Create' in the folder dialog")
        try:
            self.page.wait_for_url(re.compile(r"/dashboards/f/[^/?]+"), timeout=15000)
        except Exception as exc:
            raise AssertionError(f"The folder page did not open after 'Create'.\n{self._where_are_we()}") from exc
        return re.search(r"/dashboards/f/([^/?]+)", self.page.url).group(1)

    @step("Open folder {folder_uid}")
    def open_folder(self, folder_uid: str):
        self.page.goto(f"/dashboards/f/{folder_uid}/")
        return self

    @step("Move dashboard {dashboard_uid} into the folder '{target_title}'")
    def move_dashboard(self, dashboard_uid: str, target_title: str):
        """Needs the dashboard's current folder to be open."""
        self._select_by_uid(dashboard_uid)
        self._click(self.page.get_by_test_id("data-testid browse dashboards move button"), "the 'Move' button")
        self._click(self.page.get_by_test_id("data-testid folder-picker-trigger-button"), "the folder picker")
        self._click(self.page.get_by_role("treeitem", name=target_title), f"folder '{target_title}' in the picker")
        self._click(self.page.get_by_role("button", name="Move", exact=True), "'Move' in the dialog")
        return self

    @step("Delete the folder '{title}' (typing '{confirmation}' to confirm)")
    def delete_folder(self, folder_uid: str, title: str, confirmation: str = "delete"):
        self.page.goto(f"{self.path}?query={quote(title)}")  # filter so the folder is on screen
        self._select_by_name(title)
        self._click(self.page.get_by_test_id("data-testid browse dashboards delete button"), "the 'Delete' button")
        box = self.page.get_by_test_id("data-testid Confirm Modal Input")
        self._click(box, "the delete confirmation box")
        box.fill(confirmation)
        self._click(self.page.get_by_test_id("data-testid Confirm Modal Danger Button"), "the confirm button")
        return self
