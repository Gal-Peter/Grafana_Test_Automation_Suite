"""Browser fixtures: login-once session, per-test context with tracing/video, Allure evidence, AI triage."""
from __future__ import annotations

import shutil

import allure
import pytest
from playwright.sync_api import expect

from ai.failure_analyzer import analyze_failure
from page_objects.dashboard_page import DashboardPage
from page_objects.dashboards_browse_page import DashboardsBrowsePage
from page_objects.datasources_page import DataSourcesPage
from page_objects.explore_page import ExplorePage
from page_objects.home_page import HomePage
from page_objects.login_page import LoginPage
from utils.artifacts import safe_name
from utils.settings import keep_artifact


@pytest.fixture(scope="session", autouse=True)
def _expect_timeout(settings):
    expect.set_options(timeout=settings.default_timeout_ms)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, settings):
    return {**browser_context_args, "base_url": settings.base_url, "viewport": {"width": 1440, "height": 900}}


@pytest.fixture(scope="session")
def auth_state(playwright, settings, grafana_api, tmp_path_factory) -> str:
    """Log in ONCE through the API and reuse the session cookie in every test context."""
    path = tmp_path_factory.mktemp("auth") / "state.json"
    req = playwright.request.new_context(base_url=settings.base_url)
    resp = req.post("/login", data={"user": settings.username, "password": settings.password})
    if not resp.ok:
        pytest.exit(f"Login failed ({resp.status}). Check GF_USER / GF_PASSWORD.", returncode=1)
    req.storage_state(path=str(path))
    req.dispose()
    return str(path)


def _test_failed(node) -> bool:
    return any(getattr(node, f"rep_{phase}", None) is not None and getattr(node, f"rep_{phase}").failed
               for phase in ("setup", "call"))


def _attach_failure_evidence(pages, node, settings) -> None:
    aria = ""
    for i, page in enumerate(pages):
        try:
            allure.attach(page.screenshot(full_page=True), name=f"screenshot-{i}",
                          attachment_type=allure.attachment_type.PNG)
            if i == 0:
                aria = page.locator("body").aria_snapshot()
                allure.attach(aria, name="aria-snapshot", attachment_type=allure.attachment_type.TEXT)
        except Exception:
            pass
    if pages:
        report = getattr(node, "rep_call", None)
        analysis = analyze_failure(
            settings,
            test_id=node.nodeid,
            error_text=getattr(report, "longreprtext", "") if report else "",
            url=pages[0].url,
            aria_snapshot=aria,
        )
        if analysis:
            allure.attach(analysis, name="AI failure analysis", attachment_type=allure.attachment_type.TEXT)


@pytest.fixture
def context(browser, browser_name, browser_context_args, settings, auth_state, request):
    node = request.node
    name = safe_name(node)
    allure.dynamic.parameter("browser", browser_name)
    allure.dynamic.tag(browser_name)

    video_tmp = settings.videos_dir / ".tmp" / name
    args = {**browser_context_args}
    if not node.get_closest_marker("no_auth"):
        args["storage_state"] = auth_state
    if settings.video != "off":
        args["record_video_dir"] = str(video_tmp)

    ctx = browser.new_context(**args)
    ctx.set_default_timeout(settings.default_timeout_ms)
    if settings.trace != "off":
        ctx.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield ctx

    failed = _test_failed(node)
    pages = list(ctx.pages)
    videos = [p.video for p in pages if p.video]

    if failed:
        _attach_failure_evidence(pages, node, settings)

    if settings.trace != "off":
        if keep_artifact(settings.trace, failed):
            settings.traces_dir.mkdir(parents=True, exist_ok=True)
            trace_file = settings.traces_dir / f"{name}.zip"
            ctx.tracing.stop(path=str(trace_file))
            allure.attach.file(str(trace_file), name="playwright-trace (playwright show-trace <file>)",
                               attachment_type="application/zip", extension="zip")
        else:
            ctx.tracing.stop()
    ctx.close()

    if keep_artifact(settings.video, failed):  # video files are finalised only after the context is closed
        settings.videos_dir.mkdir(parents=True, exist_ok=True)
        for i, video in enumerate(videos):
            try:
                target = settings.videos_dir / f"{name}{'' if i == 0 else f'_{i}'}.webm"
                video.save_as(str(target))
                allure.attach.file(str(target), name="video", attachment_type=allure.attachment_type.WEBM)
            except Exception:
                pass
    shutil.rmtree(video_tmp, ignore_errors=True)


# -- page-object fixtures (dependency injection) -------------------------------
@pytest.fixture
def login_page(page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def home_page(page) -> HomePage:
    return HomePage(page)


@pytest.fixture
def dashboard_page(page) -> DashboardPage:
    return DashboardPage(page)


@pytest.fixture
def dashboards_browse_page(page) -> DashboardsBrowsePage:
    return DashboardsBrowsePage(page)


@pytest.fixture
def datasources_page(page) -> DataSourcesPage:
    return DataSourcesPage(page)


@pytest.fixture
def explore_page(page) -> ExplorePage:
    return ExplorePage(page)
