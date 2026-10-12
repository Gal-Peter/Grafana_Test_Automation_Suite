"""Turns parsed Allure results into statistics + analysis.

Two layers:
  1. build_summary / heuristic_analysis - deterministic, always available (no API key needed)
  2. ai_enrich                          - Claude refines the verdict, root causes and suggestions
If the AI call fails for any reason the report still renders from layer 1.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from ai.allure_parser import CaseResult, RunData
from ai.llm_client import get_llm_client
from utils.settings import Settings

STATUSES = ["passed", "failed", "broken", "skipped", "unknown"]

CATEGORY_RULES = [
    ("Environment / connectivity",
     r"ConnectionError|ECONNREFUSED|ERR_CONNECTION|net::ERR|Max retries exceeded|not reachable|Connection refused"),
    ("Mobile / Appium", r"WebDriverException|SessionNotCreated|InvalidSession|appium|selenium"),
    ("Locator / timing",
     r"Locator expected|waiting for (locator|get_by|selector)|Timeout \d+ms exceeded|TimeoutException|NoSuchElement|strict mode violation"),
    ("API contract", r"GrafanaApiError|status_code|/api/|returned \d{3}"),
    ("Test data / setup", r"KeyError|sqlite3|FileNotFoundError|json\.decoder|csv|fixture '"),
    ("Assertion", r"AssertionError|assert "),
]

GUIDANCE = {
    "Environment / connectivity": (
        "The test could not reach a dependency (Grafana, Appium or the network).",
        "Confirm Grafana is up before the run, raise `startup_wait_seconds` in config.json, and check BASE_URL."),
    "Mobile / Appium": (
        "The Appium session or device failed, which usually points at emulator or driver setup rather than Grafana.",
        "Check the emulator is booted, the Appium server runs with chromedriver autodownload, and MOBILE_BASE_URL is reachable from the device."),
    "Locator / timing": (
        "An element was not found, hidden, or did not appear in time. Typical after a Grafana UI change.",
        "Re-inspect the page with `python -m utils.inspect_page`, prefer role/test-id locators, and fix the page object rather than adding sleeps."),
    "API contract": (
        "The Grafana API returned a status or payload the test did not expect.",
        "Compare the expected status in the data source with what Grafana 13.x actually returns, and review the request payload."),
    "Test data / setup": (
        "The failure happened in data loading or fixture setup, before the product was exercised.",
        "Validate CSV/SQLite data (unique ids, correct columns) and re-seed with `python -m utils.db_seed --force`."),
    "Assertion": (
        "The product behaved differently from the expectation in the test.",
        "Reproduce manually; decide whether it is a product defect or an outdated expectation, then fix accordingly."),
    "Unclassified": (
        "The failure did not match a known pattern.",
        "Open the trace and screenshot attached in Allure to find the first unexpected state."),
}


def classify(text: str) -> str:
    for category, pattern in CATEGORY_RULES:
        if re.search(pattern, text, re.I):
            return category
    return "Unclassified"


def _label(c: CaseResult) -> str:
    return c.name if c.browser == "n/a" else f"{c.name} [{c.browser}]"


def _normalise(message: str) -> str:
    first = (message.splitlines() or [""])[0]
    return re.sub(r"\d+", "N", first)[:160]


def build_summary(run: RunData) -> dict:
    cases = run.cases
    total = len(cases)
    counts = Counter(c.status if c.status in STATUSES else "unknown" for c in cases)
    failing = [c for c in cases if c.failing]

    def breakdown(key) -> dict[str, dict]:
        out: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
        for c in cases:
            bucket = out[key(c) or "n/a"]
            bucket["total"] += 1
            bucket["passed"] += c.status == "passed"
            bucket["failed"] += c.failing
        return dict(sorted(out.items()))

    groups: dict[tuple, dict] = {}
    for c in failing:
        category = classify(f"{c.message}\n{c.trace}")
        key = (category, _normalise(c.message))
        g = groups.setdefault(key, {"category": category, "message": c.message[:500], "count": 0, "tests": [],
                                    "features": set(), "browsers": set(), "failed_steps": set()})
        g["count"] += 1
        g["tests"].append(_label(c))
        g["features"].add(c.feature or "n/a")
        g["browsers"].add(c.browser)
        if c.failed_step:
            g["failed_steps"].add(c.failed_step)
    failure_groups = sorted(groups.values(), key=lambda g: -g["count"])
    for i, g in enumerate(failure_groups, 1):
        g.update(id=i, tests=g["tests"][:10], features=sorted(g["features"]), browsers=sorted(g["browsers"]),
                 failed_steps=sorted(g["failed_steps"])[:3])

    by_history: dict[str, set] = defaultdict(set)
    for c in cases:
        if c.history_id:
            by_history[c.history_id].add(c.status)
    flaky = sorted({c.name for c in cases if len(by_history.get(c.history_id, ())) > 1})

    starts = [c.start for c in cases if c.start]
    stops = [c.stop for c in cases if c.stop]
    wall = (max(stops) - min(starts)) / 1000.0 if starts and stops else 0.0
    executed = total - counts["skipped"]
    return {
        "total": total,
        "counts": {s: counts.get(s, 0) for s in STATUSES},
        "pass_rate": round(100.0 * counts["passed"] / executed, 1) if executed else 0.0,
        "wall_seconds": round(wall, 1),
        "by_feature": breakdown(lambda c: c.feature),
        "by_browser": breakdown(lambda c: c.browser),
        "slowest": [{"name": _label(c), "seconds": round(c.duration_s, 1)}
                    for c in sorted(cases, key=lambda c: -c.duration_s)[:8]],
        "failure_groups": failure_groups,
        "flaky": flaky,
        "environment": run.environment,
    }


def heuristic_analysis(summary: dict) -> dict:
    counts, total, rate = summary["counts"], summary["total"], summary["pass_rate"]
    failed = counts["failed"] + counts["broken"]
    groups = summary["failure_groups"]

    if total == 0:
        risk = "unknown"
    elif failed == 0:
        risk = "low"
    elif rate >= 90 and not any(g["category"] == "Environment / connectivity" for g in groups):
        risk = "medium"
    else:
        risk = "high"

    headline = (f"{total} tests executed: {counts['passed']} passed, {failed} failed, {counts['skipped']} skipped "
                f"(pass rate {rate}%).")
    if groups:
        headline += f" Failures collapse into {len(groups)} distinct cause(s); the largest is " \
                    f"'{groups[0]['category']}' affecting {groups[0]['count']} test(s)."
    elif total:
        headline += " No failures, so this run supports a release decision."

    findings: list[str] = []
    for cat, n in Counter(g["category"] for g in groups for _ in range(g["count"])).most_common(3):
        findings.append(f"{n} failure(s) fall under '{cat}'.")
    weak = [(k, v) for k, v in summary["by_feature"].items() if v["failed"]]
    if weak:
        k, v = max(weak, key=lambda kv: kv[1]["failed"] / max(1, kv[1]["total"]))
        findings.append(f"Weakest area: '{k}' with {v['failed']} of {v['total']} test(s) failing.")
    if summary["slowest"]:
        s = summary["slowest"][0]
        findings.append(f"Slowest test: '{s['name']}' at {s['seconds']}s.")
    if summary["flaky"]:
        findings.append(f"{len(summary['flaky'])} test(s) gave mixed results across retries (flaky).")
    env = summary["environment"]
    if env.get("grafana.version"):
        findings.append(f"Tested against Grafana {env['grafana.version']}.")

    cats = {g["category"] for g in groups}
    improvements: list[dict] = []

    def add(area, suggestion, priority):
        improvements.append({"area": area, "suggestion": suggestion, "priority": priority})

    if "Locator / timing" in cats:
        add("Locators", "Stabilise page-object locators: prefer get_by_role / test ids, fix them in page_objects/ only, never add fixed sleeps.", "high")
    if "Environment / connectivity" in cats:
        add("Environment", "Add a readiness check and retry in CI before the first test, and surface Grafana logs on failure.", "high")
    if "API contract" in cats:
        add("API tests", "Re-verify expected status codes against Grafana 13.x; keep them in the SQLite table so they are easy to update.", "medium")
    if "Test data / setup" in cats:
        add("Test data", "Add a CI step that validates CSV/SQLite data (unique ids, required columns) before tests run.", "medium")
    if "Mobile / Appium" in cats:
        add("Mobile", "Pin emulator image and Appium driver versions to avoid environment drift.", "medium")
    if summary["flaky"]:
        add("Flakiness", "Quarantine flaky tests with a marker and add pytest-rerunfailures, then fix their root causes.", "high")
    if summary["slowest"] and summary["slowest"][0]["seconds"] > 20:
        add("Speed", "Move setup into API calls and run independent tests in parallel with pytest-xdist.", "medium")
    if counts["skipped"]:
        add("Coverage", f"{counts['skipped']} test(s) were skipped (for example no Appium server). Make sure that is intentional.", "low")
    if failed == 0 and total:
        add("Coverage", "Everything passed: next, add UI tests for dashboard create-edit-delete flows and for sharing content with teams.", "low")
    add("Trending", "Archive allure-results per scheduled run so pass rate and duration can be compared over time.", "low")

    failure_analysis = []
    for g in groups:
        cause, fix = GUIDANCE.get(g["category"], GUIDANCE["Unclassified"])
        failure_analysis.append({"id": g["id"], "root_cause": cause, "fix": fix})
    return {"source": "rules", "executive_summary": headline, "risk": risk, "key_findings": findings,
            "failure_analysis": failure_analysis, "improvements": improvements, "note": ""}


SYSTEM_PROMPT = (
    "You are a senior QA lead reviewing an automated test run of Grafana (Playwright + Appium, Python/pytest). "
    "You receive aggregated results as JSON. Respond with ONLY a JSON object, no markdown, with keys: "
    '"executive_summary" (2-4 sentences, plain language), "risk" ("low"|"medium"|"high"), '
    '"key_findings" (list of short strings), '
    '"failure_analysis" (list of {"id": <failure group id>, "root_cause": str, "fix": str}), '
    '"improvements" (list of {"area": str, "suggestion": str, "priority": "high"|"medium"|"low"}). '
    "Base everything on the data; say when evidence is thin instead of guessing."
)


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start:end + 1])


def ai_enrich(summary: dict, base: dict, settings: Settings) -> dict:
    """Merge Claude's analysis over the rule-based one; never raises."""
    client = get_llm_client(settings)
    if client is None:
        base["note"] = ("Rule-based analysis (AI provider is 'none'; set AI_PROVIDER=ollama, custom or anthropic)."
                        if settings.ai_provider == "none"
                        else f"Rule-based analysis (provider '{settings.ai_provider}' has no credentials).")
        return base
    try:
        payload = {k: summary[k] for k in ("total", "counts", "pass_rate", "wall_seconds", "by_feature",
                                           "by_browser", "slowest", "failure_groups", "flaky", "environment")}
        reply = client.complete(SYSTEM_PROMPT, json.dumps(payload, default=list)[:14000], max_tokens=2500)
        data = _extract_json(reply)

        merged = dict(base, source="ai", note=f"Analysis generated by {settings.ai_provider} / {settings.ai_model}.")
        if isinstance(data.get("executive_summary"), str) and data["executive_summary"].strip():
            merged["executive_summary"] = data["executive_summary"].strip()
        if data.get("risk") in {"low", "medium", "high"}:
            merged["risk"] = data["risk"]
        if isinstance(data.get("key_findings"), list) and data["key_findings"]:
            merged["key_findings"] = [str(x) for x in data["key_findings"]][:8]
        ai_fa = {int(i["id"]): i for i in data.get("failure_analysis", []) if isinstance(i, dict) and "id" in i}
        merged["failure_analysis"] = [
            {"id": f["id"], "root_cause": str(ai_fa.get(f["id"], f)["root_cause"]), "fix": str(ai_fa.get(f["id"], f)["fix"])}
            for f in base["failure_analysis"]]
        imps = [{"area": str(i.get("area", "General")), "suggestion": str(i.get("suggestion", "")),
                 "priority": i.get("priority") if i.get("priority") in {"high", "medium", "low"} else "medium"}
                for i in data.get("improvements", []) if isinstance(i, dict) and i.get("suggestion")]
        if imps:
            merged["improvements"] = imps
        return merged
    except Exception as exc:
        base["note"] = f"AI analysis unavailable ({type(exc).__name__}: {str(exc)[:160]}); showing rule-based analysis."
        return base


def analyse(run: RunData, settings: Settings, use_ai: bool = True) -> tuple[dict, dict]:
    summary = build_summary(run)
    analysis = heuristic_analysis(summary)
    if use_ai:
        analysis = ai_enrich(summary, analysis, settings)
    else:
        analysis["note"] = "Rule-based analysis (AI disabled)."
    return summary, analysis
