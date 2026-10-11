"""AI agent #1: triages a failed UI test and attaches a root-cause hypothesis to the Allure report."""
from __future__ import annotations

from ai.llm_client import get_llm_client
from utils.settings import Settings

SYSTEM = (
    "You are a senior SDET triaging a failed Playwright test against Grafana. "
    "Given the error and an ARIA snapshot of the page at failure time, answer in markdown with: "
    "1) Most likely root cause, 2) Category (product bug / locator drift / timing / test data / environment), "
    "3) A concrete suggested fix. Be concise and say when you are unsure."
)


def analyze_failure(settings: Settings, *, test_id: str, error_text: str, url: str, aria_snapshot: str) -> str | None:
    if not settings.ai_failure_analysis:
        return None
    try:
        client = get_llm_client(settings)
        if client is None:
            return (f"AI analysis skipped: provider '{settings.ai_provider}' is not usable "
                    "(set AI_PROVIDER=ollama, custom or anthropic and its settings; see README).")
        prompt = (
            f"Test: {test_id}\nURL at failure: {url}\n\n"
            f"Error:\n{error_text[-3500:]}\n\n"
            f"ARIA snapshot (truncated):\n{aria_snapshot[:6000]}"
        )
        return client.complete(SYSTEM, prompt)
    except Exception as exc:  # analysis must never break the test run
        return f"AI analysis unavailable: {type(exc).__name__}: {exc}"
