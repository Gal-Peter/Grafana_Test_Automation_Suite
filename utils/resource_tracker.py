"""Unit-of-work style cleanup stack: register undo actions, run them LIFO at teardown."""
from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)


class ResourceTracker:
    def __init__(self) -> None:
        self._stack: list[tuple[Callable, tuple]] = []

    def register(self, fn: Callable, *args) -> None:
        self._stack.append((fn, args))

    def cleanup(self) -> None:
        while self._stack:
            fn, args = self._stack.pop()
            try:
                fn(*args)
            except Exception as exc:  # cleanup must never mask the real test result
                log.warning("Cleanup %s%s failed: %s", fn.__name__, args, exc)
