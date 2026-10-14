"""Creating and editing dashboards in the UI. Locators come from a Playwright codegen recording on Grafana 13.2.2."""
from __future__ import annotations

from playwright.sync_api import Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class DashboardEditorPage(BasePage):
    path = "/dashboard/new"

    # -- actions -------------------------------------------------------------
    @step("Start a new dashboard from the Dashboards page")
    def open_new_from_ui(self):
        self.page.goto("/dashboards")  # direct URL: the side-menu link may be collapsed in a fresh browser
        self._click(self.page.get_by_test_id("data-testid CreateNewButton New button"), "the 'New' button")
        self._click(self.page.get_by_test_id("data-testid CreateNewButton New dashboard link"), "'New dashboard'")
        self.page.wait_for_load_state("networkidle")
        return self

    @property
    def configure_panel_button(self) -> Locator:
        return self.page.get_by_test_id("data-testid UnconfiguredPanel action-button configure")

    def _wait_for_configure_button(self, timeout_ms: int) -> bool:
        try:
            self.configure_panel_button.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    @step("Add a visualization (opens the panel editor)")
    def add_visualization(self):
        """A new Grafana 13 dashboard is empty: the 'Add' pane on the right has a 'Panel' button that adds a panel,
        and the panel then shows a 'configure' button. If that does not work, toggling the layout
        (Auto grid, then Custom grid) also creates one - that is what the codegen recording did."""
        self.page.get_by_role("heading", name="New dashboard", level=1).wait_for(state="visible")
        if not self._wait_for_configure_button(1500):
            self._click(self.page.get_by_role("button", name="Panel", exact=True), "the 'Add new panel' button")
        if not self._wait_for_configure_button(8000):
            self._click(self.page.get_by_role("button", name="Auto grid"), "'Auto grid'")
            self._click(self.page.get_by_role("button", name="Custom grid"), "'Custom grid'")
        if not self._wait_for_configure_button(8000):
            raise AssertionError(f"No panel 'configure' button appeared after adding a panel.\n{self._where_are_we()}")
        self._click(self.configure_panel_button, "the panel 'configure' button")
        return self

    @step("Save the dashboard as '{title}'")
    def save(self, title: str, description: str | None = None):
        self._click(self.page.get_by_test_id("data-testid Save dashboard button"), "'Save dashboard'")
        self.page.get_by_test_id("data-testid Save dashboard title field").fill(title)
        if description:
            self.page.get_by_role("textbox", name="Save dashboard description").fill(description)
        self._click(self.page.get_by_test_id("data-testid Save dashboard drawer button"), "the save button in the drawer")
        return self

    @step("Go back to the Dashboards list")
    def back_to_dashboards(self):
        self._click(self.page.get_by_test_id("data-testid Dashboards breadcrumb"), "the 'Dashboards' breadcrumb")
        return self

    # -- editing an EXISTING dashboard (Grafana 13 sidebar) -----------------------
    @step("Switch the open dashboard to edit mode")
    def start_editing(self):
        self._click(self.page.get_by_test_id("data-testid Edit dashboard button"), "the 'Edit' button")
        return self

    @step("Rename the dashboard to '{title}'")
    def rename(self, title: str):
        self._click(self.page.get_by_test_id("data-testid Dashboard Sidebar options button"),
                    "the dashboard 'Options' button in the sidebar")
        field = self.page.get_by_role("textbox", name="Title")
        field.fill(title)
        field.blur()  # Grafana commits the value when the field loses focus
        return self

    @step("Add a panel titled '{title}'")
    def add_panel(self, title: str, description: str | None = None):
        self._click(self.page.get_by_test_id("data-testid Dashboard Sidebar new button"), "the sidebar 'New' button")
        self._click(self.page.get_by_test_id("data-testid sidebar add new panel"), "'Add new panel' in the sidebar")
        field = self.page.get_by_test_id("data-testid Panel editor option pane field input Title")
        field.fill(title)
        field.blur()
        if description:
            box = self.page.get_by_role("textbox", name="Description")
            box.fill(description)
            box.blur()
        self._click(self.page.get_by_test_id("data-testid Sidebar go back"), "'Go back' in the sidebar")
        return self

    @step("Add a custom variable '{name}' with values {values}")
    def add_custom_variable(self, name: str, values: str):
        """Needs edit mode. The 'Add variable' button lives in the dashboard (it is a button, not in the sidebar)."""
        self._click(self.page.get_by_role("button", name="Add variable"), "'Add variable'")
        self._click(self.page.get_by_test_id("data-testid variable type custom").get_by_role("button", name="Custom"),
                    "the 'Custom' variable type")
        self.page.get_by_test_id("data-testid variable name input").fill(name)
        self._click(self.page.get_by_test_id("data-testid custom-variable-options-open-button"),
                    "the custom variable 'Values' editor")
        box = self.page.get_by_test_id("data-testid custom-variable-input")
        self._click(box, "the custom variable values box")
        box.fill(values)
        self._click(self.page.get_by_test_id("data-testid custom-variable-apply-button"), "'Apply' for the values")
        return self

    @step("Save the changes")
    def save_changes(self, message: str | None = None):
        self._click(self.page.get_by_test_id("data-testid Save dashboard button"), "'Save dashboard'")
        if message:
            self.page.get_by_role("textbox", name="message").fill(message)
        self._click(self.page.get_by_test_id("data-testid Save dashboard drawer button"), "the save button in the drawer")
        return self

    # -- deleting -------------------------------------------------------------
    @step("Open the full dashboard settings")
    def open_settings(self):
        self._click(self.page.get_by_test_id("data-testid Dashboard Sidebar options button"),
                    "the dashboard 'Options' button in the sidebar")
        self._click(self.page.get_by_role("button", name="View all settings"), "'View all settings'")
        return self

    @step("Delete the dashboard (typing '{confirmation}' to confirm)")
    def delete_dashboard(self, confirmation: str = "delete"):
        self._click(self.page.get_by_test_id("data-testid Dashboard settings page delete dashboard button"),
                    "'Delete dashboard' in the settings")
        box = self.page.get_by_test_id("data-testid Confirm Modal Input")
        self._click(box, "the delete confirmation box")
        box.fill(confirmation)
        box.press("Enter")
        return self
