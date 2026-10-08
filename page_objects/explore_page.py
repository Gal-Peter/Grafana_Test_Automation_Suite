from __future__ import annotations

import json

from page_objects.base_page import BasePage
from utils.allure_helpers import step


class ExplorePage(BasePage):
    path = "/explore"

    @step("Open Explore with scenario '{scenario}'")
    def open_with_query(self, ds_uid: str, ds_type: str, scenario: str):
        ds = {"type": ds_type, "uid": ds_uid}
        panes = {"a": {"datasource": ds_uid,
                       "queries": [{"refId": "A", "datasource": ds, "scenarioId": scenario}],
                       "range": {"from": "now-1h", "to": "now"}}}
        self.page.goto(f"/explore?schemaVersion=1&orgId=1&panes={json.dumps(panes)}")
        return self

    @step("Run query")
    def run_query(self):
        """Returns the /api/ds/query response so tests can assert on the backend result."""
        with self.page.expect_response(lambda r: "/api/ds/query" in r.url) as info:
            self.page.get_by_role("button", name="Run query").click()
        return info.value
