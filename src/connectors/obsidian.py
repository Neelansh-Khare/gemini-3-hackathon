"""Obsidian connector — read markdown, append structured sections."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..lifegraph.normalize import obsidian_note_to_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_obsidian_notes


class ObsidianConnector(BaseConnector):
    name = "obsidian"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.APPEND}

    def __init__(self, vault_path: str | None = None) -> None:
        self._vault_path = Path(vault_path) if vault_path else None
        self._mock_notes: list[dict] = copy.deepcopy(seed_obsidian_notes())

    def reset(self) -> None:
        self._mock_notes = copy.deepcopy(seed_obsidian_notes())

    def list_notes(self) -> list[dict]:
        if not self._vault_path or not self._vault_path.exists():
            return self._mock_notes
        
        notes = []
        for p in self._vault_path.rglob("*.md"):
            try:
                content = p.read_text(encoding="utf-8")
                notes.append({
                    "path": str(p.relative_to(self._vault_path)),
                    "title": p.stem,
                    "body": content
                })
            except Exception:
                continue
        return notes

    async def sync_to_graph(self) -> list[Entity]:
        return [obsidian_note_to_entity(n) for n in self.list_notes()]

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = diff.get("operation", "")
        payload = diff.get("payload", diff.get("after", {}))
        if diff.get("system", diff.get("connector")) not in ("obsidian", None):
            return {"ok": False, "error": "wrong_connector"}
        
        if op in ("append", "create"):
            path_str = payload.get("path") or payload.get("target_path") or "journal/append.md"
            section = payload.get("section", "## Plan")
            body = payload.get("body", "")
            block = f"\n{section}\n{body}\n"
            
            if self._vault_path and self._vault_path.exists():
                full_path = self._vault_path / path_str
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write(block)
                return {"ok": True, "path": path_str, "preview": block[:500], "real": True}
            
            # Mock fallback
            for n in self._mock_notes:
                if n["path"] == path_str:
                    n["body"] = (n.get("body") or "") + block
                    return {"ok": True, "path": path_str, "preview": block[:500], "real": False}
            self._mock_notes.append({"path": path_str, "title": path_str, "body": block})
            return {"ok": True, "path": path_str, "preview": block[:500], "real": False}
            
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    async def rollback(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        path_str = diff.get("target_id") or diff.get("payload", {}).get("path")
        if not path_str:
            return {"ok": False, "error": "path_required"}
        
        if op == "append":
            payload = diff.get("payload", {})
            section = payload.get("section", "## Plan")
            body = payload.get("body", "")
            block = f"\n{section}\n{body}\n"
            
            if self._vault_path and self._vault_path.exists():
                full_path = self._vault_path / path_str
                if full_path.exists():
                    content = full_path.read_text(encoding="utf-8")
                    if block in content:
                        new_content = content.replace(block, "", 1)
                        full_path.write_text(new_content, encoding="utf-8")
                        return {"ok": True, "rolled_back": path_str, "real": True}
                return {"ok": False, "error": "file_not_found_or_block_mismatch"}

            # Mock fallback
            for n in self._mock_notes:
                if n["path"] == path_str:
                    if block in n.get("body", ""):
                        n["body"] = n["body"].replace(block, "", 1)
                        return {"ok": True, "rolled_back": path_str, "real": False}
        elif op == "create":
            if self._vault_path and self._vault_path.exists():
                full_path = self._vault_path / path_str
                if full_path.exists():
                    full_path.unlink()
                    return {"ok": True, "rolled_back": path_str, "real": True}

            for i, n in enumerate(self._mock_notes):
                if n["path"] == path_str:
                    self._mock_notes.pop(i)
                    return {"ok": True, "rolled_back": path_str, "real": False}
                    
        return {"ok": False, "error": "unsupported_rollback", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "obsidian"
