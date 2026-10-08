"""Decorator that turns page-object methods into Allure steps."""
from __future__ import annotations

import functools
import inspect

import allure


def step(title: str | None = None):
    """@step("Log in as {username}") - placeholders are filled from the method arguments."""

    def decorator(fn):
        default = fn.__name__.replace("_", " ").capitalize()
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            name = title or default
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                name = name.format(**bound.arguments)
            except Exception:
                pass
            with allure.step(name):
                return fn(*args, **kwargs)

        return wrapper

    return decorator
