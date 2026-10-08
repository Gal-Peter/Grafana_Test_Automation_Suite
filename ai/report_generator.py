"""Renders the analysis as ONE self-contained HTML file (inline CSS + SVG, no external assets).
All dynamic text is HTML-escaped."""
from __future__ import annotations

import math
from datetime import datetime
from html import escape as e

COLORS = {"passed": "#22c55e", "failed": "#ef4444", "broken": "#f59e0b", "skipped": "#94a3b8", "unknown": "#a78bfa"}
RISK_LABEL = {"low": "Low risk", "medium": "Medium risk", "high": "High risk", "unknown": "No data"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

CSS = """
:root{--bg:#f4f6fb;--card:#fff;--text:#0f172a;--muted:#64748b;--line:#e2e8f0;--accent:#6366f1;
--ok:#22c55e;--bad:#ef4444;--warn:#f59e0b;--shadow:0 1px 3px rgba(15,23,42,.08),0 8px 24px rgba(15,23,42,.06)}
@media (prefers-color-scheme:dark){:root{--bg:#0b1020;--card:#131a2e;--text:#e6eaf5;--muted:#93a0bd;--line:#26304d;
--shadow:0 1px 3px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.hero{background:linear-gradient(135deg,#4f46e5,#7c3aed 55%,#db2777);color:#fff;padding:36px 24px 70px}
.wrap{max-width:1100px;margin:0 auto}.hero h1{margin:0 0 6px;font-size:28px;letter-spacing:-.02em}
.hero p{margin:0;opacity:.85}.badges{margin-top:14px;display:flex;gap:8px;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);padding:3px 12px;border-radius:99px;font-size:13px}
main{max-width:1100px;margin:-44px auto 40px;padding:0 20px}
.grid{display:grid;gap:16px}.kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:16px}
.card{background:var(--card);border-radius:16px;box-shadow:var(--shadow);padding:20px;border:1px solid var(--line)}
.kpi .v{font-size:30px;font-weight:700;letter-spacing:-.02em}.kpi .l{color:var(--muted);font-size:13px}
.two{grid-template-columns:repeat(auto-fit,minmax(320px,1fr));margin-bottom:16px}
h2{margin:0 0 12px;font-size:18px}h3{margin:0 0 6px;font-size:15px}
.verdict{display:inline-block;padding:3px 12px;border-radius:99px;font-weight:600;font-size:13px;margin-bottom:10px}
.risk-low{background:#dcfce7;color:#166534}.risk-medium{background:#fef3c7;color:#92400e}
.risk-high{background:#fee2e2;color:#991b1b}.risk-unknown{background:#e2e8f0;color:#334155}
.donut{display:flex;align-items:center;gap:20px;flex-wrap:wrap}.legend{list-style:none;margin:0;padding:0}
.legend li{display:flex;align-items:center;gap:8px;margin:3px 0}.dot{width:10px;height:10px;border-radius:50%}
.bar-row{margin:10px 0}.bar-row .top{display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px}
.bar{height:10px;border-radius:99px;background:var(--line);overflow:hidden;display:flex}
.bar i{display:block;height:100%}.muted{color:var(--muted)}
ul.findings{margin:0;padding-left:18px}ul.findings li{margin:5px 0}
details{border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0;background:var(--card)}
summary{cursor:pointer;font-weight:600;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.chip{font-size:12px;font-weight:600;padding:2px 10px;border-radius:99px;background:rgba(99,102,241,.14);color:var(--accent)}
.chip.count{background:rgba(239,68,68,.14);color:var(--bad)}
pre{background:rgba(100,116,139,.12);padding:10px 12px;border-radius:10px;overflow:auto;font-size:12.5px;white-space:pre-wrap}
.fix{border-left:3px solid var(--ok);padding-left:12px;margin:10px 0}.cause{border-left:3px solid var(--warn);padding-left:12px;margin:10px 0}
.imps{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.imp{border-left:5px solid var(--muted)}.imp.high{border-color:var(--bad)}.imp.medium{border-color:var(--warn)}.imp.low{border-color:var(--ok)}
.pri{font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:700;color:var(--muted)}
footer{text-align:center;color:var(--muted);font-size:13px;padding:10px 20px 30px}
@media print{.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}details{break-inside:avoid}}
"""


def _donut(counts: dict, total: int, rate: float) -> str:
    r, cx = 54, 70
    circ = 2 * math.pi * r
    parts, offset = [], 0.0
    if total:
        for status, n in counts.items():
            if n:
                length = circ * n / total
                parts.append(f'<circle r="{r}" cx="{cx}" cy="{cx}" fill="none" stroke="{COLORS[status]}" '
                             f'stroke-width="16" stroke-dasharray="{length:.2f} {circ - length:.2f}" '
                             f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cx})"/>')
                offset += length
    else:
        parts.append(f'<circle r="{r}" cx="{cx}" cy="{cx}" fill="none" stroke="#cbd5e1" stroke-width="16"/>')
    legend = "".join(f'<li><span class="dot" style="background:{COLORS[s]}"></span>{e(s.title())}: <b>{n}</b></li>'
                     for s, n in counts.items() if n)
    return (f'<div class="donut"><svg width="140" height="140" viewBox="0 0 140 140" role="img" '
            f'aria-label="Pass rate {rate}%">{"".join(parts)}'
            f'<text x="70" y="68" text-anchor="middle" font-size="24" font-weight="700" fill="currentColor">{rate:g}%</text>'
            f'<text x="70" y="88" text-anchor="middle" font-size="11" fill="#94a3b8">pass rate</text></svg>'
            f'<ul class="legend">{legend}</ul></div>')


def _bars(breakdown: dict) -> str:
    if not breakdown:
        return '<p class="muted">No data.</p>'
    rows = []
    for label, v in breakdown.items():
        total = max(1, v["total"])
        ok, bad = 100 * v["passed"] / total, 100 * v["failed"] / total
        rows.append(f'<div class="bar-row"><div class="top"><span>{e(label)}</span>'
                    f'<span class="muted">{v["passed"]}/{v["total"]} passed</span></div>'
                    f'<div class="bar"><i style="width:{ok:.1f}%;background:var(--ok)"></i>'
                    f'<i style="width:{bad:.1f}%;background:var(--bad)"></i></div></div>')
    return "".join(rows)


def _slowest(items: list[dict]) -> str:
    if not items:
        return '<p class="muted">No data.</p>'
    top = max(i["seconds"] for i in items) or 1
    return "".join(f'<div class="bar-row"><div class="top"><span>{e(i["name"])}</span>'
                   f'<span class="muted">{i["seconds"]}s</span></div><div class="bar">'
                   f'<i style="width:{100 * i["seconds"] / top:.1f}%;background:var(--accent)"></i></div></div>'
                   for i in items)


def _failures(summary: dict, analysis: dict) -> str:
    groups = summary["failure_groups"]
    if not groups:
        return '<p class="muted">No failures in this run.</p>'
    by_id = {f["id"]: f for f in analysis["failure_analysis"]}
    out = []
    for g in groups:
        a = by_id.get(g["id"], {})
        tests = "".join(f"<li>{e(t)}</li>" for t in g["tests"])
        steps = f'<p class="muted">Failed step: {e(", ".join(g["failed_steps"]))}</p>' if g["failed_steps"] else ""
        out.append(
            f'<details{" open" if g["id"] == 1 else ""}><summary><span class="chip">{e(g["category"])}</span>'
            f'<span class="chip count">{g["count"]} test(s)</span>'
            f'<span class="muted">{e(", ".join(g["features"]))} · {e(", ".join(g["browsers"]))}</span></summary>'
            f'<pre>{e(g["message"])}</pre>{steps}'
            f'<div class="cause"><b>Likely root cause</b><br>{e(a.get("root_cause", ""))}</div>'
            f'<div class="fix"><b>Suggested fix</b><br>{e(a.get("fix", ""))}</div>'
            f'<p class="muted" style="margin-bottom:4px">Affected tests</p><ul class="findings">{tests}</ul></details>')
    return "".join(out)


def _improvements(items: list[dict]) -> str:
    ordered = sorted(items, key=lambda i: PRIORITY_ORDER.get(i["priority"], 3))
    return "".join(f'<div class="card imp {e(i["priority"])}"><div class="pri">{e(i["priority"])} priority · {e(i["area"])}</div>'
                   f'<p style="margin:6px 0 0">{e(i["suggestion"])}</p></div>' for i in ordered)


def render_html(summary: dict, analysis: dict, title: str = "Grafana Test Run: AI Analysis") -> str:
    c, total = summary["counts"], summary["total"]
    failed = c["failed"] + c["broken"]
    env = summary["environment"]
    risk = analysis["risk"] if analysis["risk"] in RISK_LABEL else "unknown"
    source = "AI-assisted analysis" if analysis["source"] == "ai" else "Rule-based analysis"
    badges = "".join(f'<span class="badge">{e(t)}</span>' for t in [
        source, f'Grafana {env["grafana.version"]}' if env.get("grafana.version") else "",
        env.get("grafana.url", ""), f"Generated {datetime.now():%Y-%m-%d %H:%M}"] if t)
    kpis = [("Total tests", total), ("Passed", c["passed"]), ("Failed / broken", failed),
            ("Skipped", c["skipped"]), ("Pass rate", f'{summary["pass_rate"]:g}%'),
            ("Wall time", f'{summary["wall_seconds"]:g}s')]
    kpi_html = "".join(f'<div class="card kpi"><div class="v">{e(str(v))}</div><div class="l">{e(l)}</div></div>'
                       for l, v in kpis)
    findings = "".join(f"<li>{e(f)}</li>" for f in analysis["key_findings"]) or '<li class="muted">None.</li>'
    note = f'<p class="muted" style="margin-top:12px;font-size:13px">{e(analysis["note"])}</p>' if analysis["note"] else ""

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<style>{CSS}</style></head><body>
<header class="hero"><div class="wrap"><h1>{e(title)}</h1>
<p>Automated analysis of the Allure results with findings and recommended improvements</p>
<div class="badges">{badges}</div></div></header>
<main>
<section class="grid kpis">{kpi_html}</section>
<section class="grid two">
 <div class="card"><span class="verdict risk-{risk}">{RISK_LABEL[risk]}</span>
  <h2>Executive summary</h2><p>{e(analysis["executive_summary"])}</p>
  <h3>Key findings</h3><ul class="findings">{findings}</ul>{note}</div>
 <div class="card"><h2>Results</h2>{_donut(c, total, summary["pass_rate"])}</div>
</section>
<section class="grid two">
 <div class="card"><h2>By feature</h2>{_bars(summary["by_feature"])}</div>
 <div class="card"><h2>By browser / device</h2>{_bars(summary["by_browser"])}</div>
</section>
<section class="card" style="margin-bottom:16px"><h2>Failure analysis</h2>{_failures(summary, analysis)}</section>
<h2 style="margin:22px 4px 10px">Suggested improvements</h2>
<section class="grid imps">{_improvements(analysis["improvements"])}</section>
<section class="card" style="margin-top:16px"><h2>Slowest tests</h2>{_slowest(summary["slowest"])}</section>
</main><footer>Generated from allure-results by ai/report_generator.py</footer></body></html>"""
