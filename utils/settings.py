"""Central configuration (Singleton via lru_cache).

Precedence: environment variable  >  config.json  >  built-in default.
Secrets (GITHUB_TOKEN, ANTHROPIC_API_KEY, AI_API_KEY) are read from the environment / .env only, never from config.json.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # .env support is optional
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(ROOT / ".env")

POLICIES = {"off", "on", "retain-on-failure"}


def _load_json() -> dict:
    path = Path(os.getenv("CONFIG_FILE") or ROOT / "config.json")
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _val(cfg: dict, env: str, section: str, key: str, default: Any = None) -> Any:
    raw = os.getenv(env)
    if raw not in (None, ""):
        return raw
    value = (cfg.get(section) or {}).get(key, default)
    return default if value in (None, "") else value


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _policy(value: Any, name: str) -> str:
    v = str(value).strip().lower()
    if v not in POLICIES:
        raise ValueError(f"{name} must be one of {sorted(POLICIES)}, got '{v}'")
    return v


def _path(value: Any) -> Path:
    p = Path(str(value))
    return p if p.is_absolute() else ROOT / p


@dataclass(frozen=True)
class Settings:
    base_url: str
    username: str
    password: str
    testdata_type: str
    startup_wait_s: int
    default_timeout_ms: int
    trace: str
    video: str
    allure_dir: Path
    traces_dir: Path
    videos_dir: Path
    logs_dir: Path
    ai_report_path: Path
    data_dir: Path
    sqlite_path: Path
    ai_provider: str
    ai_api_key: str | None
    ai_base_url: str
    ai_model: str
    ai_max_calls: int
    ai_failure_analysis: bool
    ai_report_analysis: bool
    appium_url: str
    mobile_platform: str
    mobile_device: str
    mobile_platform_version: str | None
    mobile_udid: str | None
    mobile_base_url: str


AI_PROVIDERS = {"none", "github", "ollama", "anthropic"}
AI_DEFAULT_MODEL = {"none": "", "github": "openai/gpt-4.1-mini", "ollama": "llama3.1:8b", "anthropic": "claude-sonnet-5-5"}


def _ai_api_key(provider: str) -> str | None:
    explicit = os.getenv("AI_API_KEY")
    if explicit:
        return explicit
    env_name = {"github": ("GITHUB_TOKEN", "GH_MODELS_TOKEN"), "anthropic": ("ANTHROPIC_API_KEY",)}.get(provider, ())
    return next((os.getenv(n) for n in env_name if os.getenv(n)), None)


def _ai_base_url(provider: str, configured: str) -> str:
    if configured:
        return configured.rstrip("/")
    if provider == "github":
        return "https://models.github.ai/inference"
    if provider == "ollama":  # inside Docker, "localhost" is the container itself
        host = "host.docker.internal" if Path("/.dockerenv").exists() else "localhost"
        return f"http://{host}:11434/v1"
    return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    c = _load_json()
    ai_provider = str(_val(c, "AI_PROVIDER", "ai", "provider", "none")).strip().lower()
    if ai_provider not in AI_PROVIDERS:
        raise ValueError(f"AI_PROVIDER must be one of {sorted(AI_PROVIDERS)}, got '{ai_provider}'")
    platform = str(_val(c, "MOBILE_PLATFORM", "mobile", "platform", "android")).lower()
    if platform not in {"android", "ios"}:
        raise ValueError("MOBILE_PLATFORM must be 'android' or 'ios'")
    # Android emulators reach the host machine at 10.0.2.2; iOS simulators share the host's localhost
    mobile_base = _val(c, "MOBILE_BASE_URL", "mobile", "base_url",
                       "http://10.0.2.2:3000" if platform == "android" else "http://localhost:3000")
    return Settings(
        base_url=str(_val(c, "BASE_URL", "grafana", "base_url", "http://localhost:3000")).rstrip("/"),
        username=str(_val(c, "GF_USER", "grafana", "username", "admin")),
        password=str(_val(c, "GF_PASSWORD", "grafana", "password", "admin")),
        testdata_type=str(_val(c, "GF_TESTDATA_TYPE", "grafana", "testdata_type", "grafana-testdata-datasource")),
        startup_wait_s=int(_val(c, "GRAFANA_WAIT_SECONDS", "grafana", "startup_wait_seconds", 10)),
        default_timeout_ms=int(_val(c, "DEFAULT_TIMEOUT_MS", "playwright", "default_timeout_ms", 15000)),
        trace=_policy(_val(c, "TRACE", "playwright", "trace", "retain-on-failure"), "TRACE"),
        video=_policy(_val(c, "VIDEO", "playwright", "video", "retain-on-failure"), "VIDEO"),
        allure_dir=_path(_val(c, "ALLURE_DIR", "paths", "allure_results", "allure-results")),
        traces_dir=_path(_val(c, "TRACES_DIR", "paths", "traces", "traces")),
        videos_dir=_path(_val(c, "VIDEOS_DIR", "paths", "videos", "videos")),
        logs_dir=_path(_val(c, "LOGS_DIR", "paths", "logs", "logs")),
        ai_report_path=_path(_val(c, "AI_REPORT_PATH", "paths", "ai_report", "logs/ai_report.html")),
        data_dir=_path(_val(c, "TEST_DATA_DIR", "paths", "test_data", "tests/data")),
        sqlite_path=_path(_val(c, "SQLITE_DB", "paths", "sqlite_db", "tests/data/test_data.db")),
        ai_provider=ai_provider,
        ai_api_key=_ai_api_key(ai_provider),
        ai_base_url=_ai_base_url(ai_provider, str(_val(c, "AI_BASE_URL", "ai", "base_url", ""))),
        ai_model=str(_val(c, "AI_MODEL", "ai", "model", AI_DEFAULT_MODEL[ai_provider])),
        ai_max_calls=int(_val(c, "AI_MAX_CALLS", "ai", "max_calls", 10)),
        ai_failure_analysis=_bool(_val(c, "AI_FAILURE_ANALYSIS", "ai", "failure_analysis", False)),
        ai_report_analysis=_bool(_val(c, "AI_REPORT_ANALYSIS", "ai", "report_analysis", True)),
        appium_url=str(_val(c, "APPIUM_URL", "mobile", "appium_url", "http://127.0.0.1:4723")).rstrip("/"),
        mobile_platform=platform,
        mobile_device=str(_val(c, "MOBILE_DEVICE", "mobile", "device", "Android Emulator")),
        mobile_platform_version=_val(c, "MOBILE_PLATFORM_VERSION", "mobile", "platform_version", None),
        mobile_udid=_val(c, "MOBILE_UDID", "mobile", "udid", None),
        mobile_base_url=str(mobile_base).rstrip("/"),
    )


def keep_artifact(policy: str, test_failed: bool) -> bool:
    """Retention policy decision shared by trace and video."""
    return policy == "on" or (policy == "retain-on-failure" and test_failed)
