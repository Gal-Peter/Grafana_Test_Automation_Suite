"""Factory pattern: builds an Appium driver for the configured platform."""
from __future__ import annotations

from appium import webdriver

from utils.settings import Settings


def create_driver(settings: Settings):
    if settings.mobile_platform == "android":
        from appium.options.android import UiAutomator2Options

        opts = UiAutomator2Options()
        opts.platform_name = "Android"
        opts.browser_name = "Chrome"
        opts.device_name = settings.mobile_device
        opts.set_capability("appium:chromedriverAutodownload", True)
        opts.set_capability("goog:chromeOptions", {"args": ["--no-first-run", "--disable-fre",
                                                            "--no-default-browser-check"]})
    else:
        from appium.options.ios import XCUITestOptions

        opts = XCUITestOptions()
        opts.platform_name = "iOS"
        opts.browser_name = "Safari"
        opts.device_name = settings.mobile_device

    if settings.mobile_udid:
        opts.udid = settings.mobile_udid
    if settings.mobile_platform_version:
        opts.platform_version = settings.mobile_platform_version
    opts.new_command_timeout = 180
    return webdriver.Remote(settings.appium_url, options=opts)
