import os

import allure
import pytest

from ai.exploratory_agent import ExploratoryAgent
from ai.llm_client import LLMUnavailable, get_llm_client


@allure.epic("Grafana")
@allure.feature("AI exploratory testing")
@pytest.mark.ai
@pytest.mark.parametrize("mission", [
    "Explore the dashboards browse page and the Explore page; check that they load without errors.",
])
def test_ai_exploration_finds_no_critical_issues(mission, page, settings):
    client = get_llm_client(settings)
    if client is None:
        message = ("AI provider not configured. Set AI_PROVIDER=ollama (local, free) or custom/anthropic "
                   "in .env; see README 'Staying on the free tier'.")
        if os.getenv("REQUIRE_AI"):  # set by the docker compose ai-tests service
            pytest.fail(message, pytrace=False)
        pytest.skip(message)

    page.goto("/")
    try:
        report = ExploratoryAgent(client, page).run(mission)
    except LLMUnavailable as exc:
        message = f"AI provider unavailable, so no exploration took place: {exc}"
        if os.getenv("REQUIRE_AI"):
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    allure.attach(report.to_markdown(), name="Exploratory report", attachment_type=allure.attachment_type.TEXT)

    serious = [i for i in report.issues if i["severity"] in {"high", "critical"}]
    assert not serious, f"Agent reported serious issues: {serious}"
