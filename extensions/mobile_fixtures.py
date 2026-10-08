"""Appium fixtures: server gate, driver with auth + screen recording, Allure evidence, AI triage."""
from __future__ import annotations

import base64
import os

import allure
import pytest
import requests

from ai.failure_analyzer import analyze_failure
from utils.settings import keep_artifact
from page_objects.mobile.dashboard_screen import DashboardScreen
from page_objects.mobile.driver_factory import create_driver
from page_objects.mobile.login_screen import LoginScreen
from utils.artifacts import safe_name


def _appium_up(url: str) -> bool:
    try:
        return requests.get(f"{url}/status", timeout=3).ok
    except requests.RequestException:
        return False


def _session_cookie(settings) -> dict:
    """Log in through the API (host URL) and reuse the session cookie inside the mobile browser."""
    session = requests.Session()
    resp = session.post(f"{settings.base_url}/login",
                        json={"user": settings.username, "password": settings.password}, timeout=15)
    resp.raise_for_status()
    value = session.cookies.get("grafana_session")
    if not value:
        raise RuntimeError("No grafana_session cookie returned by /login")
    return {"name": "grafana_session", "value": value, "path": "/"}


def _failed(node) -> bool:
    return any(getattr(node, f"rep_{p}", None) is not None and getattr(node, f"rep_{p}").failed
               for p in ("setup", "call"))


@pytest.fixture
def mobile_driver(settings, grafana_api, request):
    node = request.node
    if not _appium_up(settings.appium_url):
        message = (f"No Appium server reachable at {settings.appium_url}. Start it on the host "
                   f"(see README 'Mobile tests in Docker') or run: python -m utils.mobile_check")
        if os.getenv("REQUIRE_MOBILE"):  # set by the docker compose mobile service: fail, don't hide it as a skip
            pytest.fail(message, pytrace=False)
        pytest.skip(message)

    allure.dynamic.parameter("device", f"{settings.mobile_platform}:{settings.mobile_device}")
    allure.dynamic.tag("mobile")
    driver = create_driver(settings)
    recording = settings.video != "off"
    try:
        if recording:
            driver.start_recording_screen()
        if not node.get_closest_marker("no_auth"):
            driver.get(settings.mobile_base_url + "/login")  # cookie needs a page on the right domain
            driver.add_cookie(_session_cookie(settings))
        yield driver

        failed = _failed(node)
        name = safe_name(node)
        source = ""
        if failed:
            try:
                allure.attach(driver.get_screenshot_as_png(), name="screenshot",
                              attachment_type=allure.attachment_type.PNG)
                source = driver.page_source
                allure.attach(source, name="page-source", attachment_type=allure.attachment_type.XML)
                report = getattr(node, "rep_call", None)
                analysis = analyze_failure(settings, test_id=node.nodeid,
                                           error_text=getattr(report, "longreprtext", "") if report else "",
                                           url=driver.current_url, aria_snapshot=source)
                if analysis:
                    allure.attach(analysis, name="AI failure analysis", attachment_type=allure.attachment_type.TEXT)
            except Exception:
                pass
        if recording:
            try:
                raw = driver.stop_recording_screen()
                if keep_artifact(settings.video, failed):
                    settings.videos_dir.mkdir(parents=True, exist_ok=True)
                    path = settings.videos_dir / f"{name}.mp4"
                    path.write_bytes(base64.b64decode(raw))
                    allure.attach.file(str(path), name="screen-recording",
                                       attachment_type=allure.attachment_type.MP4)
            except Exception:
                pass
    finally:
        driver.quit()


@pytest.fixture
def mobile_login_screen(mobile_driver, settings) -> LoginScreen:
    return LoginScreen(mobile_driver, settings.mobile_base_url)


@pytest.fixture
def mobile_dashboard_screen(mobile_driver, settings) -> DashboardScreen:
    return DashboardScreen(mobile_driver, settings.mobile_base_url)
