"""Prints ARIA snapshots and data-testid values for key Grafana pages so you can fix locators fast.

Usage:  python -m utils.inspect_page            (uses config.json / .env)
        python -m utils.inspect_page /explore   (extra paths)
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

from utils.grafana_client import GrafanaClient
from utils.dashboard_builder import DashboardBuilder
from utils.settings import get_settings

s = get_settings()
PATHS = ["/login", "/", "/dashboards", "/connections/datasources", "/explore"] + sys.argv[1:]

api = GrafanaClient(s.base_url, s.username, s.password, s.testdata_type)
print("Grafana version:", api.health().get("version"))

folder = api.create_folder("inspect-tmp")
builder = DashboardBuilder().in_folder(folder["uid"]).add_panel("Inspect Panel")
api.create_dashboard(builder.build())
PATHS.append(f"/d/{builder.uid}")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        req = p.request.new_context(base_url=s.base_url)
        req.post("/login", data={"user": s.username, "password": s.password})
        state = req.storage_state()
        for path in PATHS:
            ctx = browser.new_context(base_url=s.base_url, storage_state=None if path == "/login" else state)
            page = ctx.new_page()
            page.goto(path)
            page.wait_for_load_state("networkidle")
            ids = sorted({e.get_attribute("data-testid") for e in page.locator("[data-testid]").all()
                          if e.get_attribute("data-testid")})
            print(f"\n{'=' * 78}\n{path}  ->  {page.url}\n{'=' * 78}")
            print(page.locator("body").aria_snapshot()[:3500])
            print("\n-- data-testid values --")
            print("\n".join(ids[:80]))
            ctx.close()
        browser.close()
finally:
    api.delete_folder(folder["uid"])
