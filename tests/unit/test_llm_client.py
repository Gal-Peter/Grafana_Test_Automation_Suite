from dataclasses import replace

import pytest

import ai.llm_client as llm
from utils.settings import get_settings

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, str(payload)

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _fresh_budget():
    llm.reset_budget()


def _settings(**changes):
    return replace(get_settings(), **changes)


def test_provider_none_makes_no_client_so_nothing_can_be_billed():
    assert llm.get_llm_client(_settings(ai_provider="none", ai_api_key="irrelevant")) is None


def test_hosted_providers_need_credentials():
    assert llm.get_llm_client(_settings(ai_provider="github", ai_api_key=None)) is None


def test_ollama_needs_no_key():
    client = llm.get_llm_client(_settings(ai_provider="ollama", ai_api_key=None, ai_base_url="http://x/v1"))
    assert client is not None and client.name == "ollama"


def test_openai_compatible_text_and_tool_call_parsing(monkeypatch):
    replies = iter([
        FakeResponse({"choices": [{"message": {"content": "hello"}}]}),
        FakeResponse({"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "goto", "arguments": '{"path": "/dashboards"}'}}]}}]}),
    ])
    sent = []
    monkeypatch.setattr(llm.requests, "post", lambda url, **kw: (sent.append((url, kw)), next(replies))[1])
    client = llm.get_llm_client(_settings(ai_provider="github", ai_api_key="t", ai_model="m",
                                          ai_base_url="https://models.github.ai/inference"))

    assert client.complete("sys", "hi") == "hello"
    assert sent[0][0] == "https://models.github.ai/inference/chat/completions"
    assert sent[0][1]["headers"]["Authorization"] == "Bearer t"

    messages = [{"role": "user", "content": "go"}]
    turn = client.chat("sys", messages, [{"name": "goto", "description": "d", "input_schema": {"type": "object"}}])
    assert [(c.name, c.args) for c in turn.tool_calls] == [("goto", {"path": "/dashboards"})]
    client.add_assistant(messages, turn)
    client.add_tool_results(messages, [(turn.tool_calls[0], "ok")])
    assert messages[-1] == {"role": "tool", "tool_call_id": "c1", "content": "ok"}
    assert sent[1][1]["json"]["tools"][0]["function"]["name"] == "goto"


def test_call_budget_stops_runaway_usage(monkeypatch):
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResponse({"choices": [{"message": {"content": "x"}}]}))
    client = llm.get_llm_client(_settings(ai_provider="ollama", ai_base_url="http://x/v1", ai_max_calls=2))
    client.complete("s", "p")
    client.complete("s", "p")
    with pytest.raises(RuntimeError, match="budget"):
        client.complete("s", "p")


def test_http_errors_surface_clearly(monkeypatch):
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResponse({"error": "rate limited"}, status=429))
    client = llm.get_llm_client(_settings(ai_provider="github", ai_api_key="t", ai_base_url="http://x"))
    with pytest.raises(RuntimeError, match="429"):
        client.complete("s", "p")
