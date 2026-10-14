"""Factory helpers for unique, collision-free test data."""
from __future__ import annotations

from uuid import uuid4


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def alert_rule_payload(folder_uid: str, datasource: dict, testdata_type: str, title: str | None = None) -> dict:
    ds = {"type": testdata_type, "uid": datasource["uid"]}
    expr = {"type": "__expr__", "uid": "__expr__"}
    return {
        "title": unique_name("auto-rule") if title is None else title, "ruleGroup": unique_name("auto-group"), "folderUID": folder_uid,
        "orgID": 1, "condition": "C", "for": "1m", "noDataState": "NoData", "execErrState": "Error",
        "data": [
            {"refId": "A", "relativeTimeRange": {"from": 600, "to": 0}, "datasourceUid": datasource["uid"],
             "model": {"refId": "A", "scenarioId": "random_walk", "datasource": ds}},
            {"refId": "B", "datasourceUid": "__expr__",
             "model": {"refId": "B", "type": "reduce", "expression": "A", "reducer": "last", "datasource": expr}},
            {"refId": "C", "datasourceUid": "__expr__",
             "model": {"refId": "C", "type": "threshold", "expression": "B", "datasource": expr,
                       "conditions": [{"evaluator": {"type": "gt", "params": [1000000]}}]}},
        ],
    }
