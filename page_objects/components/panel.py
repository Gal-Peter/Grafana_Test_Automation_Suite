from __future__ import annotations

from playwright.sync_api import Page

from page_objects.components.base_component import BaseComponent


class Panel(BaseComponent):
    """A dashboard panel, located by its title.

    Grafana 13 ships the new "dynamic dashboards" layout engine by default, so the classic
    data-testid may or may not be present. We accept either it or an accessible heading with the title.
    """

    def __init__(self, page: Page, title: str):
        classic = page.get_by_test_id(f"data-testid Panel header {title}")
        by_heading = page.get_by_role("heading", name=title, exact=True)
        super().__init__(page, classic.or_(by_heading).first)
        self.title = title

    @property
    def header(self):
        return self.root
