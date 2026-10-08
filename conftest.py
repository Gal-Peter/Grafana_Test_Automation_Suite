"""Root conftest: registers the plugins that live in extensions/."""
pytest_plugins = [
    "extensions.reporting_hooks",
    "extensions.api_fixtures",
    "extensions.browser_fixtures",
    "extensions.mobile_fixtures",
]
