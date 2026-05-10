"""Gmail connector: read threads, create draft replies only (no send in MVP)."""

from __future__ import annotations

import copy
import base64
from typing import Any
from uuid import uuid4

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

from .google_utils import get_google_credentials
from ..lifegraph.normalize import gmail_thread_to_entity, gmail_draft_entity
from ..lifegraph.schema import Entity
from .base import BaseConnector, ConnectorCapability
from .seed import seed_gmail_drafts, seed_gmail_threads


class GmailConnector(BaseConnector):
    """Gmail — real API if credentials available, else mock."""

    name = "gmail"
    capabilities = {ConnectorCapability.READ, ConnectorCapability.WRITE}

    def __init__(self, token_path: str = "token.json", creds_path: str = "credentials.json") -> None:
        self._token_path = token_path
        self._creds_path = creds_path
        self._creds = get_google_credentials(token_path, creds_path)
        self._service = build("gmail", "v1", credentials=self._creds) if self._creds and build else None
        
        self._threads: list[dict] = copy.deepcopy(seed_gmail_threads())
        self._drafts: list[dict] = copy.deepcopy(seed_gmail_drafts())

    def reset(self) -> None:
        self._threads = copy.deepcopy(seed_gmail_threads())
        self._drafts = copy.deepcopy(seed_gmail_drafts())

    def list_threads(self) -> list[dict]:
        if not self._service:
            return self._threads
        
        try:
            results = self._service.users().threads().list(userId="me", maxResults=10).execute()
            threads = []
            for t in results.get("threads", []):
                full_t = self._service.users().threads().get(userId="me", id=t["id"]).execute()
                msg = full_t["messages"][0]
                headers = msg["payload"]["headers"]
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
                
                snippet = msg.get("snippet", "")
                threads.append({
                    "id": t["id"],
                    "subject": subject,
                    "sender": sender,
                    "body": snippet,
                    "timestamp": msg.get("internalDate")
                })
            return threads
        except Exception:
            return self._threads

    def list_drafts(self) -> list[dict]:
        if not self._service:
            return self._drafts
        
        try:
            results = self._service.users().drafts().list(userId="me", maxResults=10).execute()
            drafts = []
            for d in results.get("drafts", []):
                full_d = self._service.users().drafts().get(userId="me", id=d["id"]).execute()
                msg = full_d["message"]
                headers = msg["payload"]["headers"]
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                to = next((h["value"] for h in headers if h["name"].lower() == "to"), "")
                
                drafts.append({
                    "id": d["id"],
                    "subject": subject,
                    "to": to,
                    "body": msg.get("snippet", ""),
                    "is_draft": True
                })
            return drafts
        except Exception:
            return self._drafts

    async def sync_to_graph(self) -> list[Entity]:
        out: list[Entity] = []
        for t in self.list_threads():
            out.append(gmail_thread_to_entity(t))
        for d in self.list_drafts():
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
            
        if self._service:
            try:
                if op in ("draft", "create", "append", "update"):
                    message_text = (
                        f"To: {payload.get('to', '')}\r\n"
                        f"Subject: {payload.get('subject', 'Re: Draft')}\r\n\r\n"
                        f"{payload.get('body', '')}"
                    )
                    message = {
                        "message": {
                            "raw": base64.urlsafe_b64encode(message_text.encode()).decode()
                        }
                    }
                    draft = self._service.users().drafts().create(userId="me", body=message).execute()
                    return {"ok": True, "draft_id": draft["id"], "preview": payload.get("body", "")[:500], "real": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        # Mock fallback
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
            return {"ok": True, "draft_id": draft_id, "preview": draft["body"][:500], "real": False}
        return {"ok": False, "error": "unsupported_op", "diff": diff}

    async def rollback(self, diff: dict[str, Any]) -> dict[str, Any]:
        op = str(diff.get("operation", "")).lower()
        tid = diff.get("target_id")
        if not tid:
            return {"ok": False, "error": "target_id_required"}
            
        if self._service:
            try:
                self._service.users().drafts().delete(userId="me", id=tid).execute()
                return {"ok": True, "rolled_back": tid, "real": True}
            except Exception:
                pass

        if op in ("draft", "create", "append", "update"):
            for i, d in enumerate(self._drafts):
                if d["id"] == tid:
                    self._drafts.pop(i)
                    return {"ok": True, "rolled_back": tid, "real": False}
        return {"ok": False, "error": "unsupported_rollback", "diff": diff}

    def can_handle(self, system: str) -> bool:
        return system.lower() == "gmail"
