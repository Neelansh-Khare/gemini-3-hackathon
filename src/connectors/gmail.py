"""Gmail connector: read threads, create draft replies only (no send in MVP)."""

from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4

from ..lifegraph.normalize import gmail_thread_to_entity, gmail_draft_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_gmail_drafts, seed_gmail_threads


class GmailConnector(BaseConnector):
    """Mock Gmail — threads + drafts; apply_diff adds drafts."""

    name = "gmail"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.WRITE}

    def __init__(self) -> None:
        self._threads: list[dict] = copy.deepcopy(seed_gmail_threads())
        self._drafts: list[dict] = copy.deepcopy(seed_gmail_drafts())

    def reset(self) -> None:
        self._threads = copy.deepcopy(seed_gmail_threads())
        self._drafts = copy.deepcopy(seed_gmail_drafts())

    def list_threads(self) -> list[dict]:
        return self._threads

    def list_drafts(self) -> list[dict]:
        return self._drafts

    async def sync_to_graph(self) -> list[Entity]:
        out: list[Entity] = []
        for t in self._threads:
            out.append(gmail_thread_to_entity(t))
        for d in self._drafts:
            d2 = dict(d)
            d2["is_draft"] = True
            out.append(gmail_draft_entity(d2))
        return out

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", diff.get("op", ""))).lower()
        payload = diff.get("payload", diff.get("after", {}))
        sysname = (diff.get("connector") or diff.get("system") or "").lower()
        if sysname and sysname != "gmail":
            return {"ok": False, "error": "wrong_connector"}
        if op in ("draft", "create", "append", "update"):
            draft_id = str(uuid4())[:8]
            draft = {
                "id": draft_id,
                "subject": payload.get("subject", "Re: Draft"),
                "body": payload.get("body", ""),
                "to": payload.get("to", ""),
                "thread_id": payload.get("thread_id"),
                "is_draft": True,
            }
            self._drafts.append(draft)
            return {"ok": True, "draft_id": draft_id, "preview": draft["body"][:500]}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "gmail"
