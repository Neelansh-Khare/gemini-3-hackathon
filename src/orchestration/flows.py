"""Execute approved tool operations with connector routing and audit logging."""

from __future__ import annotations

from typing import Any

from ..audit.audit_log import AuditLog
from ..domain.prd_models import ConnectorName, OperationKind, ToolOperation
from ..connectors.calendar import CalendarConnector
from ..connectors.gmail import GmailConnector
from ..connectors.notion import NotionConnector
from ..connectors.obsidian import ObsidianConnector
from ..lifegraph.storage import LifeGraphStorage
from ..lifegraph.normalize import normalize_connector_record


def _op_to_diff(op: ToolOperation) -> dict[str, Any]:
    return {
        "connector": op.connector.value,
        "system": op.connector.value,
        "operation": op.operation.value,
        "payload": op.payload,
        "target_id": op.target_id,
    }


def _connector_for(
    op: ToolOperation,
    gmail: GmailConnector,
    calendar: CalendarConnector,
    notion: NotionConnector,
    obsidian: ObsidianConnector,
):
    m = {
        ConnectorName.GMAIL: gmail,
        ConnectorName.CALENDAR: calendar,
        ConnectorName.NOTION: notion,
        ConnectorName.OBSIDIAN: obsidian,
    }
    return m[op.connector]


async def execute_tool_operations(
    operations: list[ToolOperation],
    gmail: GmailConnector,
    calendar: CalendarConnector,
    notion: NotionConnector,
    obsidian: ObsidianConnector,
    audit: AuditLog | None = None,
    lifegraph: LifeGraphStorage | None = None,
) -> dict[str, Any]:
    """Apply approved operations (subset allowed)."""
    results: list[dict[str, Any]] = []
    for op in operations:
        conn = _connector_for(op, gmail, calendar, notion, obsidian)
        diff = _op_to_diff(op)
        try:
            out = await conn.apply_diff(diff)
            # Capture the target_id from the connector response
            tid = (
                out.get("event_id") 
                or out.get("notion_id") 
                or out.get("draft_id") 
                or out.get("path") 
                or op.target_id
            )
            results.append({"id": op.id, "connector": op.connector.value, "status": "ok", "result": out})
            
            if audit:
                audit.log_execution(
                    connector=op.connector,
                    operation=op.operation,
                    payload=op.payload,
                    payload_summary=op.preview[:500],
                    target_id=tid,
                    tool_operation_id=op.id,
                )
            
            # Real-time LifeGraph Sync
            if lifegraph and tid and out.get("ok"):
                # We can't always get the full record back from apply_diff easily without extra calls,
                # but we can try to sync it if it's a new entity.
                # For now, we'll use a heuristic: if it was a 'create' or 'append', 
                # we try to normalize the payload into a LifeGraph entity.
                record = {**op.payload, "id": tid}
                if op.connector == ConnectorName.GMAIL:
                    record["is_draft"] = True
                entity = normalize_connector_record(op.connector.value, record)
                if entity:
                    lifegraph.save_entity(entity)

        except Exception as e:
            results.append(
                {"id": op.id, "connector": op.connector.value, "status": "error", "error": str(e)}
            )
    return {"executed": results}


async def rollback_tool_operations(
    entry_ids: list[str],
    gmail: GmailConnector,
    calendar: CalendarConnector,
    notion: NotionConnector,
    obsidian: ObsidianConnector,
    audit: AuditLog,
    lifegraph: LifeGraphStorage | None = None,
) -> dict[str, Any]:
    """Undo specific audit log entries."""
    recent = audit.list_recent(limit=100)
    to_rollback = [e for e in recent if e.id in entry_ids]
    
    results: list[dict[str, Any]] = []
    for entry in to_rollback:
        # Mocking the connector lookup
        class DummyOp:
            def __init__(self, connector):
                self.connector = connector
        
        conn = _connector_for(DummyOp(entry.connector), gmail, calendar, notion, obsidian) # type: ignore
        diff = {
            "operation": entry.operation.value,
            "target_id": entry.target_id,
            "payload": entry.payload
        }
        try:
            out = await conn.rollback(diff)
            is_ok = out.get("ok")
            results.append({
                "entry_id": entry.id,
                "connector": entry.connector.value,
                "status": "ok" if is_ok else "error",
                "result": out
            })
            
            # Real-time LifeGraph Sync (Rollback)
            if lifegraph and is_ok and entry.target_id:
                # If we rolled back a creation, remove it from the graph
                if entry.operation in (OperationKind.CREATE, OperationKind.DRAFT):
                    # Need to map target_id back to LifeGraph ID format
                    # prefix is usually connector:id
                    lg_id = f"{entry.connector.value}:{entry.target_id}"
                    if entry.connector == ConnectorName.GMAIL:
                        lg_id = f"gmail_draft:{entry.target_id}"
                    elif entry.connector == ConnectorName.OBSIDIAN:
                        lg_id = f"obsidian:{entry.target_id}"
                    
                    lifegraph.delete_entity(lg_id)

        except Exception as e:
            results.append({
                "entry_id": entry.id,
                "connector": entry.connector.value,
                "status": "error",
                "error": str(e)
            })
            
    return {"rolled_back": results}
