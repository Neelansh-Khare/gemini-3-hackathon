"""Notion connector — query goals/tasks, append weekly plan entries."""

from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from ..lifegraph.normalize import notion_item_to_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_notion_items


class NotionConnector(BaseConnector):
    name = "notion"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.APPEND, ConnectorCapability.WRITE}

    def __init__(self) -> None:
        self._items: list[dict] = copy.deepcopy(seed_notion_items())
        self._weekly_entries: list[str] = []

    def reset(self) -> None:
        self._items = copy.deepcopy(seed_notion_items())
        self._weekly_entries = []

    def list_items(self) -> list[dict]:
        return self._items

    def weekly_plan_log(self) -> list[str]:
        return list(self._weekly_entries)

    async def sync_to_graph(self) -> list[Entity]:
        return [notion_item_to_entity(i) for i in self._items]

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = diff.get("operation", "")
        payload = diff.get("payload", diff.get("after", {}))
        if diff.get("system", diff.get("connector")) not in ("notion", None):
            return {"ok": False, "error": "wrong_connector"}
        if op in ("append", "create"):
            if "weekly_plan_line" in payload or payload.get("type") == "weekly_plan":
                line = payload.get("text") or payload.get("weekly_plan_line") or ""
                self._weekly_entries.append(line)
                return {"ok": True, "appended": "weekly_plan"}
            nid = str(uuid4())[:8]
            self._items.append(
                {
                    "id": nid,
                    "type": payload.get("item_type", "task"),
                    "title": payload.get("title", "Task"),
                    "status": "todo",
                    "due": payload.get("due"),
                }
            )
            return {"ok": True, "notion_id": nid}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "notion"
