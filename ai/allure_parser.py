"""Reads an allure-results directory (the *-result.json files written by allure-pytest)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FAILING = {"failed", "broken"}


@dataclass
class CaseResult:
    uuid: str
    name: str
    full_name: str
    status: str
    message: str = ""
    trace: str = ""
    start: int = 0
    stop: int = 0
    epic: str = ""
    feature: str = ""
    story: str = ""
    tags: list[str] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    history_id: str = ""
    failed_step: str = ""
    attachments: list[str] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return max(0.0, (self.stop - self.start) / 1000.0)

    @property
    def browser(self) -> str:
        """Browser (desktop) or device (mobile), as tagged by the fixtures."""
        return self.parameters.get("browser") or self.parameters.get("device") or "n/a"

    @property
    def failing(self) -> bool:
        return self.status in FAILING


@dataclass
class RunData:
    cases: list[CaseResult]
    environment: dict[str, str]


def _first_failed_step(steps: list[dict]) -> str:
    for step in steps or []:
        if step.get("status") in FAILING:
            return _first_failed_step(step.get("steps") or []) or step.get("name", "")
    return ""


def _collect_attachments(node: dict) -> list[str]:
    names = [a.get("name", "") for a in node.get("attachments") or []]
    for step in node.get("steps") or []:
        names += _collect_attachments(step)
    return names


def _parse_case(data: dict) -> CaseResult:
    labels: dict[str, list[str]] = {}
    for label in data.get("labels") or []:
        labels.setdefault(label.get("name", ""), []).append(str(label.get("value", "")))
    details = data.get("statusDetails") or {}
    return CaseResult(
        uuid=data.get("uuid", ""),
        name=data.get("name") or data.get("fullName") or "unnamed",
        full_name=data.get("fullName", ""),
        status=data.get("status", "unknown"),
        message=(details.get("message") or "").strip(),
        trace=(details.get("trace") or "").strip(),
        start=int(data.get("start") or 0),
        stop=int(data.get("stop") or 0),
        epic=(labels.get("epic") or [""])[0],
        feature=(labels.get("feature") or [""])[0],
        story=(labels.get("story") or [""])[0],
        tags=labels.get("tag", []),
        parameters={p.get("name", ""): str(p.get("value", ""))[:80] for p in data.get("parameters") or []},
        history_id=data.get("historyId", ""),
        failed_step=_first_failed_step(data.get("steps") or []),
        attachments=_collect_attachments(data),
    )


def load_run(results_dir: str | Path) -> RunData:
    results_dir = Path(results_dir)
    cases: list[CaseResult] = []
    for file in sorted(results_dir.glob("*-result.json")):
        try:
            cases.append(_parse_case(json.loads(file.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError):
            continue  # a half-written file must not break reporting

    env: dict[str, str] = {}
    env_file = results_dir / "environment.properties"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return RunData(cases=cases, environment=env)
