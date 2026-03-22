"""Google Calendar connector — read events, create/reschedule suggestions."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..lifegraph.normalize import calendar_event_to_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_calendar_events


class CalendarConnector(BaseConnector):
    name = "calendar"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.WRITE}

    def __init__(self) -> None:
        self._events: list[dict] = copy.deepcopy(seed_calendar_events())

    def reset(self) -> None:
        self._events = copy.deepcopy(seed_calendar_events())

    def list_events(self) -> list[dict]:
        return self._events

    async def sync_to_graph(self) -> list[Entity]:
        return [calendar_event_to_entity(e) for e in self._events]

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        payload = diff.get("payload", diff.get("after", {}))
        sysname = (diff.get("connector") or diff.get("system") or "").lower()
        if sysname and sysname != "calendar":
            return {"ok": False, "error": "wrong_connector"}
        if op in ("create", "append", "draft"):
            eid = str(uuid4())[:8]

            def _dt(v: Any) -> Any:
                if v is None:
                    return None
                if isinstance(v, datetime):
                    return v
                if isinstance(v, str):
                    try:
                        return datetime.fromisoformat(v.replace("Z", "+00:00"))
                    except ValueError:
                        return None
                return None

            ev = {
                "id": eid,
                "title": payload.get("title", "Event"),
                "start": _dt(payload.get("start")),
                "end": _dt(payload.get("end")),
                "location": payload.get("location"),
            }
            self._events.append(ev)
            return {"ok": True, "event_id": eid}
        if op == "update" and payload.get("target_id"):
            tid = payload["target_id"]
            for e in self._events:
                if e["id"] == tid:
                    if "start" in payload:
                        e["start"] = payload["start"]
                    if "end" in payload:
                        e["end"] = payload["end"]
                    return {"ok": True, "event_id": tid}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "calendar"
