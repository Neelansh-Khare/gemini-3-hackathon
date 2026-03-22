"""Append-only audit log (SQLite) for executed tool operations."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from ..domain.prd_models import AuditEntry, ConnectorName, OperationKind


class AuditLog:
    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(str(self._path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    connector TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    target_id TEXT,
                    payload_summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    tool_operation_id TEXT
                )
                """
            )
            conn.commit()

    def append(self, entry: AuditEntry) -> None:
        with sqlite3.connect(str(self._path)) as conn:
            conn.execute(
                """
                INSERT INTO audit_entries
                (id, timestamp, connector, operation, target_id, payload_summary, payload_json, tool_operation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.timestamp.isoformat(),
                    entry.connector.value,
                    entry.operation.value,
                    entry.target_id,
                    entry.payload_summary,
                    json.dumps(entry.payload),
                    entry.tool_operation_id,
                ),
            )
            conn.commit()

    def log_execution(
        self,
        *,
        connector: ConnectorName,
        operation: OperationKind,
        payload: dict,
        payload_summary: str,
        target_id: str | None = None,
        tool_operation_id: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            connector=connector,
            operation=operation,
            target_id=target_id,
            payload_summary=payload_summary,
            payload=payload,
            tool_operation_id=tool_operation_id,
        )
        self.append(entry)
        return entry

    def list_recent(self, limit: int = 100) -> list[AuditEntry]:
        with sqlite3.connect(str(self._path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM audit_entries
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out: list[AuditEntry] = []
        for r in rows:
            out.append(
                AuditEntry(
                    id=r["id"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    connector=ConnectorName(r["connector"]),
                    operation=OperationKind(r["operation"]),
                    target_id=r["target_id"],
                    payload_summary=r["payload_summary"],
                    payload=json.loads(r["payload_json"] or "{}"),
                    tool_operation_id=r["tool_operation_id"],
                )
            )
        return out
