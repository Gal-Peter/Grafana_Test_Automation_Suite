"""Provider-agnostic LLM layer (Adapter pattern).

  none       - default: NO network calls, nothing can be billed
  github     - GitHub Models, free rate-limited tier (OpenAI-compatible API; GITHUB_TOKEN works inside Actions)
  ollama     - local models on your own machine, free
  anthropic  - Claude API, PAID (pay-as-you-go) - only used if you explicitly choose it

A per-process call budget (AI_MAX_CALLS, default 10) guards against runaway usage on any provider.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests

from utils.settings import Settings

_calls_made = 0


def _spend(limit: int) -> None:
    global _calls_made
    if _calls_made >= limit:
        raise RuntimeError(f"AI call budget reached ({limit} calls). Raise AI_MAX_CALLS if that is intended.")
    _calls_made += 1


def reset_budget() -> None:
    global _calls_made
    _calls_made = 0


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class ChatTurn:
    text: str
    tool_calls: list[ToolCall]
    raw: Any = None


class BaseLLM:
    name = "base"

    def __init__(self, settings: Settings):
        self.model = settings.ai_model
        self._limit = settings.ai_max_calls

    # -- provider specific ------------------------------------------------
    def chat(self, system: str, messages: list, tools: list | None = None, max_tokens: int = 1500) -> ChatTurn:
        raise NotImplementedError

    def add_assistant(self, messages: list, turn: ChatTurn) -> None:
        raise NotImplementedError

    def add_tool_results(self, messages: list, results: list[tuple[ToolCall, str]]) -> None:
        raise NotImplementedError

    # -- shared -----------------------------------------------------------
    def complete(self, system: str, prompt: str, max_tokens: int = 1200) -> str:
        return self.chat(system, [{"role": "user", "content": prompt}], None, max_tokens).text


class OpenAICompatLLM(BaseLLM):
    """Works for GitHub Models, Ollama and any other OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, settings: Settings, name: str):
        super().__init__(settings)
        self.name = name
        self._url = f"{settings.ai_base_url}/chat/completions"
        self._key = settings.ai_api_key

    def chat(self, system, messages, tools=None, max_tokens=1500) -> ChatTurn:
        _spend(self._limit)
        payload: dict = {"model": self.model, "max_tokens": max_tokens, "temperature": 0.2,
                         "messages": [{"role": "system", "content": system}] + messages}
        if tools:
            payload["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                                   "parameters": t["input_schema"]}} for t in tools]
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        resp = requests.post(self._url, headers=headers, json=payload, timeout=180)
        if resp.status_code >= 400:
            raise RuntimeError(f"{self.name} API error {resp.status_code}: {resp.text[:300]}")
        message = resp.json()["choices"][0]["message"]
        calls = []
        for tc in message.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(tc["id"], tc["function"]["name"], args))
        return ChatTurn(text=message.get("content") or "", tool_calls=calls, raw=message)

    def add_assistant(self, messages, turn) -> None:
        entry = {"role": "assistant", "content": turn.raw.get("content")}
        if turn.raw.get("tool_calls"):
            entry["tool_calls"] = turn.raw["tool_calls"]
        messages.append(entry)

    def add_tool_results(self, messages, results) -> None:
        for call, output in results:
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})


class AnthropicLLM(BaseLLM):
    """PAID provider. Only constructed when AI_PROVIDER=anthropic."""
    name = "anthropic"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        import anthropic  # lazy: the SDK is only needed if you choose this provider

        self._client = anthropic.Anthropic(api_key=settings.ai_api_key)

    def chat(self, system, messages, tools=None, max_tokens=1500) -> ChatTurn:
        _spend(self._limit)
        kwargs = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        resp = self._client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return ChatTurn(text=text, tool_calls=calls, raw=resp.content)

    def add_assistant(self, messages, turn) -> None:
        messages.append({"role": "assistant", "content": turn.raw})

    def add_tool_results(self, messages, results) -> None:
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call.id, "content": output} for call, output in results]})


def get_llm_client(settings: Settings) -> BaseLLM | None:
    """None means 'AI is off or not configured'; callers fall back to rule-based behaviour."""
    provider = settings.ai_provider
    if provider == "none":
        return None
    if provider == "ollama":
        return OpenAICompatLLM(settings, "ollama")
    if not settings.ai_api_key:
        return None
    if provider == "github":
        return OpenAICompatLLM(settings, "github")
    if provider == "anthropic":
        return AnthropicLLM(settings)
    return None
