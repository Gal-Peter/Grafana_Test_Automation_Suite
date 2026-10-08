"""AI agent #2: an autonomous exploratory tester (LLM tool-use loop over Playwright).

Patterns: Command (each tool is a command), Adapter (BaseLLM), Template (run loop).
Safety: destructive actions are blocked by the toolbox, and the step budget is capped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from playwright.sync_api import Page

from ai.llm_client import BaseLLM

MAX_SNAPSHOT_CHARS = 6000

TOOLS = [
    {"name": "snapshot", "description": "Return the ARIA snapshot of the current page.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "goto", "description": "Navigate to a Grafana path such as /dashboards or /explore.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "click", "description": "Click an element by ARIA role and accessible name.",
     "input_schema": {"type": "object", "properties": {"role": {"type": "string"}, "name": {"type": "string"}},
                      "required": ["role", "name"]}},
    {"name": "fill", "description": "Fill an input found by its label or placeholder.",
     "input_schema": {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                      "required": ["label", "value"]}},
    {"name": "report_issue", "description": "Record a defect or UX problem you observed.",
     "input_schema": {"type": "object", "properties": {
         "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
         "description": {"type": "string"}}, "required": ["severity", "description"]}},
    {"name": "finish", "description": "End the session with a short summary.",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}},
]

SYSTEM = (
    "You are an exploratory QA agent testing a Grafana web app that is already logged in. "
    "Explore the area given in the mission using the tools, look for errors, broken pages, "
    "error banners, empty states that look wrong, or inconsistent UI. Use report_issue for real problems only. "
    "Never delete data or log out. Stop with finish() when done or after a handful of steps."
)


@dataclass
class AgentReport:
    summary: str = ""
    issues: list[dict] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        issues = "\n".join(f"- **{i['severity']}**: {i['description']}" for i in self.issues) or "- none"
        steps = "\n".join(f"{n + 1}. {s}" for n, s in enumerate(self.steps))
        return f"## Summary\n{self.summary}\n\n## Issues\n{issues}\n\n## Steps\n{steps}"


class BrowserToolbox:
    BLOCKED = re.compile(r"delete|remove|logout|sign out|reset|revoke", re.I)

    def __init__(self, page: Page, report: AgentReport):
        self.page = page
        self.report = report

    def execute(self, name: str, args: dict) -> str:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return f"Unknown tool: {name}"
        self.report.steps.append(f"{name}({args})")
        try:
            return handler(**args)
        except Exception as exc:
            return f"ERROR: {type(exc).__name__}: {str(exc)[:300]}"

    def _tool_snapshot(self) -> str:
        return self.page.locator("body").aria_snapshot()[:MAX_SNAPSHOT_CHARS]

    def _tool_goto(self, path: str) -> str:
        if self.BLOCKED.search(path):
            return "Blocked: destructive or session-ending path."
        self.page.goto(path)
        return f"Now at {self.page.url}"

    def _tool_click(self, role: str, name: str) -> str:
        if self.BLOCKED.search(name):
            return "Blocked: destructive action."
        self.page.get_by_role(role, name=name).first.click(timeout=5000)
        return f"Clicked {role} '{name}'. Now at {self.page.url}"

    def _tool_fill(self, label: str, value: str) -> str:
        target = self.page.get_by_label(label).or_(self.page.get_by_placeholder(label)).first
        target.fill(value, timeout=5000)
        return f"Filled '{label}'"

    def _tool_report_issue(self, severity: str, description: str) -> str:
        self.report.issues.append({"severity": severity, "description": description, "url": self.page.url})
        return "Issue recorded."


class ExploratoryAgent:
    def __init__(self, client: BaseLLM, page: Page, max_steps: int = 12):
        self.client = client
        self.report = AgentReport()
        self.toolbox = BrowserToolbox(page, self.report)
        self.max_steps = max_steps

    def run(self, mission: str) -> AgentReport:
        messages: list = [{"role": "user", "content": f"Mission: {mission}"}]
        for _ in range(self.max_steps):
            turn = self.client.chat(SYSTEM, messages, TOOLS, max_tokens=1000)
            self.client.add_assistant(messages, turn)
            if not turn.tool_calls:
                break
            results, done = [], False
            for call in turn.tool_calls:
                if call.name == "finish":
                    self.report.summary = call.args.get("summary", "")
                    output, done = "Session ended.", True
                else:
                    output = self.toolbox.execute(call.name, call.args)
                results.append((call, output))
            self.client.add_tool_results(messages, results)
            if done:
                break
        if not self.report.summary:
            self.report.summary = "Step budget exhausted before the agent called finish()."
        return self.report
