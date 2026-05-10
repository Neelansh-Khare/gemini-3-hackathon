"""Google Calendar connector — read events, create/reschedule suggestions."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any
from uuid import uuid4

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

from .google_utils import get_google_credentials
from ..lifegraph.normalize import calendar_event_to_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_calendar_events


class CalendarConnector(BaseConnector):
    name = "calendar"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.WRITE}

    def __init__(self, token_path: str = "token.json", creds_path: str = "credentials.json") -> None:
        self._token_path = token_path
        self._creds_path = creds_path
        self._creds = get_google_credentials(token_path, creds_path)
        self._service = build("calendar", "v3", credentials=self._creds) if self._creds and build else None
        self._events: list[dict] = copy.deepcopy(seed_calendar_events())

    def reset(self) -> None:
        self._events = copy.deepcopy(seed_calendar_events())

    def list_events(self) -> list[dict]:
        if not self._service:
            return self._events
        
        try:
            now = datetime.utcnow().isoformat() + "Z"
            events_result = self._service.events().list(
                calendarId="primary", timeMin=now, maxResults=10, singleEvents=True, orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            
            out = []
            for e in events:
                start = e["start"].get("dateTime") or e["start"].get("date")
                end = e["end"].get("dateTime") or e["end"].get("date")
                
                def _parse(v):
                    if not v: return None
                    try:
                        return datetime.fromisoformat(v.replace("Z", "+00:00"))
                    except:
                        return None

                out.append({
                    "id": e["id"],
                    "title": e.get("summary", "Untitled"),
                    "start": _parse(start),
                    "end": _parse(end),
                    "location": e.get("location"),
                })
            return out
        except Exception:
            return self._events

    async def sync_to_graph(self) -> list[Entity]:
        return [calendar_event_to_entity(e) for e in self.list_events()]

    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        payload = diff.get("payload", diff.get("after", {}))
        sysname = (diff.get("connector") or diff.get("system") or "").lower()
        if sysname and sysname != "calendar":
            return {"ok": False, "error": "wrong_connector"}
            
        if self._service:
            try:
                def _fmt(dt):
                    if isinstance(dt, datetime):
                        return dt.isoformat()
                    return dt

                if op in ("create", "append", "draft"):
                    event = {
                        "summary": payload.get("title", "Event"),
                        "location": payload.get("location"),
                        "start": {"dateTime": _fmt(payload.get("start")), "timeZone": "UTC"},
                        "end": {"dateTime": _fmt(payload.get("end")), "timeZone": "UTC"},
                    }
                    event = self._service.events().insert(calendarId="primary", body=event).execute()
                    return {"ok": True, "event_id": event["id"], "real": True}
                
                if op == "update" and payload.get("target_id"):
                    tid = payload["target_id"]
                    event = self._service.events().get(calendarId="primary", eventId=tid).execute()
                    if "title" in payload: event["summary"] = payload["title"]
                    if "start" in payload: event["start"] = {"dateTime": _fmt(payload["start"]), "timeZone": "UTC"}
                    if "end" in payload: event["end"] = {"dateTime": _fmt(payload["end"]), "timeZone": "UTC"}
                    
                    updated_event = self._service.events().update(calendarId="primary", eventId=tid, body=event).execute()
                    return {"ok": True, "event_id": tid, "real": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        # Mock fallback
        if op in ("create", "append", "draft"):
            eid = str(uuid4())[:8]
            def _dt(v: Any) -> Any:
                if v is None: return None
                if isinstance(v, datetime): return v
                if isinstance(v, str):
                    try: return datetime.fromisoformat(v.replace("Z", "+00:00"))
                    except ValueError: return None
                return None
            ev = {
                "id": eid,
                "title": payload.get("title", "Event"),
                "start": _dt(payload.get("start")),
                "end": _dt(payload.get("end")),
                "location": payload.get("location"),
            }
            self._events.append(ev)
            return {"ok": True, "event_id": eid, "real": False}
        if op == "update" and payload.get("target_id"):
            tid = payload["target_id"]
            for e in self._events:
                if e["id"] == tid:
                    if "start" in payload: e["start"] = payload["start"]
                    if "end" in payload: e["end"] = payload["end"]
                    return {"ok": True, "event_id": tid, "real": False}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    async def rollback(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        tid = diff.get("target_id")
        if not tid:
            return {"ok": False, "error": "target_id_required"}
            
        if self._service:
            try:
                self._service.events().delete(calendarId="primary", eventId=tid).execute()
                return {"ok": True, "rolled_back": tid, "real": True}
            except Exception:
                pass

        if op in ("create", "append", "draft"):
            for i, e in enumerate(self._events):
                if e["id"] == tid:
                    self._events.pop(i)
                    return {"ok": True, "rolled_back": tid, "real": False}
        return {"ok": False, "error": "unsupported_rollback", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "calendar"
