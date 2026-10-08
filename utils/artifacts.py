"""Deterministic, Windows-safe artifact names for traces / videos."""
from __future__ import annotations

import hashlib
import re


def safe_name(node) -> str:
    """Readable prefix + short hash: unique per parametrised test, short enough for Windows' 260-char limit."""
    sanitized = re.sub(r"[^\w.-]+", "_", node.nodeid)
    digest = hashlib.md5(node.nodeid.encode()).hexdigest()[:6]
    return f"{sanitized[:70]}_{digest}"
