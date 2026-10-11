"""One tiny call to confirm your AI provider works:   python -m ai.check"""
from __future__ import annotations

import sys

from ai.llm_client import LLMUnavailable, get_llm_client
from utils.settings import get_settings


def main() -> int:
    s = get_settings()
    print(f"provider={s.ai_provider}  model={s.ai_model or '-'}  url={s.ai_base_url or '-'}")
    client = get_llm_client(s)
    if client is None:
        print("No client: AI_PROVIDER is 'none' or credentials are missing (custom needs AI_BASE_URL and AI_MODEL; anthropic needs ANTHROPIC_API_KEY).")
        return 1
    try:
        print("reply:", client.complete("You are a connectivity test.", "Reply with the single word OK.", 20).strip())
        return 0
    except LLMUnavailable as exc:
        print("FAILED:", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
