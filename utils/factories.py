"""Factory helpers for unique, collision-free test data."""
from __future__ import annotations

from uuid import uuid4


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"
