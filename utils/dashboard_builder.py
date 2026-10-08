"""Builder pattern: fluent construction of a /api/dashboards/db payload."""
from __future__ import annotations

from uuid import uuid4


class DashboardBuilder:
    def __init__(self) -> None:
        suffix = uuid4().hex[:8]
        self.uid = f"auto-{suffix}"
        self.title = f"auto-dashboard-{suffix}"
        self._tags: list[str] = []
        self._panels: list[dict] = []
        self._folder_uid: str | None = None

    def with_title(self, title: str) -> "DashboardBuilder":
        self.title = title
        return self

    def with_uid(self, uid: str) -> "DashboardBuilder":
        self.uid = uid
        return self

    def with_tags(self, *tags: str) -> "DashboardBuilder":
        self._tags.extend(tags)
        return self

    def in_folder(self, folder_uid: str) -> "DashboardBuilder":
        self._folder_uid = folder_uid
        return self

    @property
    def has_folder(self) -> bool:
        return self._folder_uid is not None

    def add_panel(self, title: str, panel_type: str = "text") -> "DashboardBuilder":
        idx = len(self._panels)
        panel = {
            "id": idx + 1,
            "type": panel_type,
            "title": title,
            "gridPos": {"h": 6, "w": 12, "x": (idx % 2) * 12, "y": (idx // 2) * 6},
        }
        if panel_type == "text":
            panel["options"] = {"mode": "markdown", "content": f"Panel {title}"}
        self._panels.append(panel)
        return self

    @property
    def panel_titles(self) -> list[str]:
        return [p["title"] for p in self._panels]

    def build(self) -> dict:
        return {
            "dashboard": {
                "uid": self.uid,
                "title": self.title,
                "tags": self._tags,
                "panels": self._panels,
                "schemaVersion": 39,
                "time": {"from": "now-6h", "to": "now"},
            },
            "folderUid": self._folder_uid,
            "overwrite": False,
        }
