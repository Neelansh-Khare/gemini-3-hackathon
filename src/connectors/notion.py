"""Notion connector — query goals/tasks, append weekly plan entries."""

from __future__ import annotations

import copy
import os
from typing import Any
from uuid import uuid4

try:
    from notion_client import Client
except ImportError:
    Client = None

from ..lifegraph.normalize import notion_item_to_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_notion_items


class NotionConnector(BaseConnector):
    name = "notion"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.APPEND, ConnectorCapability.WRITE}

    def __init__(self, api_key: str | None = None, database_id: str | None = None) -> None:
        self._api_key = api_key
        self._database_id = database_id
        self._client = Client(auth=api_key) if Client and api_key else None
        self._items: list[dict] = copy.deepcopy(seed_notion_items())
        self._weekly_entries: list[str] = []

    def reset(self) -> None:
        self._items = copy.deepcopy(seed_notion_items())
        self._weekly_entries = []

    def list_items(self) -> list[dict]:
        if not self._client or not self._database_id:
            return self._items
        
        try:
            results = self._client.databases.query(database_id=self._database_id).get("results", [])
            items = []
            for page in results:
                props = page.get("properties", {})
                
                # Try multiple common title properties
                title = "Untitled"
                for title_key in ["Name", "Title", "Task", "Goal"]:
                    if title_key in props:
                        title_prop = props[title_key]
                        title_list = title_prop.get("title", []) or title_prop.get("rich_text", [])
                        if title_list:
                            title = title_list[0].get("plain_text", "Untitled")
                            break
                
                status_prop = props.get("Status", {})
                status = status_prop.get("status", {}).get("name") or status_prop.get("select", {}).get("name") or "todo"
                
                due_prop = props.get("Due", {}) or props.get("Date", {})
                due = due_prop.get("date", {}).get("start") if due_prop.get("date") else None
                
                items.append({
                    "id": page["id"],
                    "type": "task",
                    "title": title,
                    "status": status,
                    "due": due,
                    "url": page.get("url")
                })
            return items
        except Exception:
            return self._items

    def weekly_plan_log(self) -> list[str]:
        return list(self._weekly_entries)

    async def sync_to_graph(self) -> list[Entity]:
        items = self.list_items()
        return [notion_item_to_entity(i) for i in items]

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = diff.get("operation", "")
        payload = diff.get("payload", diff.get("after", {}))
        if diff.get("system", diff.get("connector")) not in ("notion", None):
            return {"ok": False, "error": "wrong_connector"}
            
        if self._client and self._database_id:
            try:
                if op in ("append", "create"):
                    if "weekly_plan_line" in payload or payload.get("type") == "weekly_plan":
                        line = payload.get("text") or payload.get("weekly_plan_line") or ""
                        self._weekly_entries.append(line)
                        return {"ok": True, "appended": "weekly_plan", "real": True}
                    
                    props = {
                        "Name": {"title": [{"text": {"content": payload.get("title", "Task")}}]},
                        "Status": {"select": {"name": payload.get("status", "todo")}},
                    }
                    if payload.get("due"):
                        props["Due"] = {"date": {"start": payload.get("due")}}
                    
                    new_page = self._client.pages.create(
                        parent={"database_id": self._database_id},
                        properties=props
                    )
                    return {"ok": True, "notion_id": new_page["id"], "real": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        # Mock fallback
        if op in ("append", "create"):
            if "weekly_plan_line" in payload or payload.get("type") == "weekly_plan":
                line = payload.get("text") or payload.get("weekly_plan_line") or ""
                self._weekly_entries.append(line)
                return {"ok": True, "appended": "weekly_plan", "real": False}
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
            return {"ok": True, "notion_id": nid, "real": False}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    async def rollback(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        tid = diff.get("target_id")
        if not tid:
            payload = diff.get("payload", {})
            if "weekly_plan_line" in payload or payload.get("type") == "weekly_plan":
                line = payload.get("text") or payload.get("weekly_plan_line") or ""
                if line in self._weekly_entries:
                    self._weekly_entries.remove(line)
                    return {"ok": True, "rolled_back": "weekly_plan_line"}
            return {"ok": False, "error": "target_id_required"}
        
        if self._client:
            try:
                # In Notion, "rollback" of a create means archive the page
                self._client.pages.update(page_id=tid, archived=True)
                return {"ok": True, "rolled_back": tid, "real": True}
            except Exception:
                pass 

        if op in ("create", "append"):
            for i, item in enumerate(self._items):
                if item["id"] == tid:
                    self._items.pop(i)
                    return {"ok": True, "rolled_back": tid, "real": False}
        return {"ok": False, "error": "unsupported_rollback", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "notion"
