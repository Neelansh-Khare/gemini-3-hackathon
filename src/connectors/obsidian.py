"""Obsidian connector — read markdown, append structured sections."""

from __future__ import annotations

import copy
from typing import Any

from ..lifegraph.normalize import obsidian_note_to_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_obsidian_notes


class ObsidianConnector(BaseConnector):
    name = "obsidian"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.APPEND}

    def __init__(self) -> None:
        self._notes: list[dict] = copy.deepcopy(seed_obsidian_notes())

    def reset(self) -> None:
        self._notes = copy.deepcopy(seed_obsidian_notes())

    def list_notes(self) -> list[dict]:
        return self._notes

    async def sync_to_graph(self) -> list[Entity]:
        return [obsidian_note_to_entity(n) for n in self._notes]

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = diff.get("operation", "")
        payload = diff.get("payload", diff.get("after", {}))
        if diff.get("system", diff.get("connector")) not in ("obsidian", None):
            return {"ok": False, "error": "wrong_connector"}
        if op in ("append", "create"):
            path = payload.get("path") or payload.get("target_path") or "journal/append.md"
            section = payload.get("section", "## Plan")
            body = payload.get("body", "")
            block = f"\n{section}\n{body}\n"
            for n in self._notes:
                if n["path"] == path:
                    n["body"] = (n.get("body") or "") + block
                    return {"ok": True, "path": path, "preview": block[:500]}
            self._notes.append({"path": path, "title": path, "body": block})
            return {"ok": True, "path": path, "preview": block[:500]}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    async def rollback(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        path = diff.get("target_id") or diff.get("payload", {}).get("path")
        if not path:
            return {"ok": False, "error": "path_required"}
        
        if op == "append":
            # For mock purposes, we just remove the appended block if we can find it
            # In a real system, we'd need more precision
            payload = diff.get("payload", {})
            section = payload.get("section", "## Plan")
            body = payload.get("body", "")
            block = f"\n{section}\n{body}\n"
            for n in self._notes:
                if n["path"] == path:
                    if block in n.get("body", ""):
                        n["body"] = n["body"].replace(block, "", 1)
                        return {"ok": True, "rolled_back": path}
        elif op == "create":
             for i, n in enumerate(self._notes):
                if n["path"] == path:
                    self._notes.pop(i)
                    return {"ok": True, "rolled_back": path}
                    
        return {"ok": False, "error": "unsupported_rollback", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "obsidian"
