"""Execute approved tool operations with connector routing and audit logging."""

from __future__ import annotations

from typing import Any

from ..audit.audit_log import AuditLog
from ..domain.prd_models import ConnectorName, OperationKind, ToolOperation
from ..connectors.calendar import CalendarConnector
from ..connectors.gmail import GmailConnector
from ..connectors.notion import NotionConnector
from ..connectors.obsidian import ObsidianConnector


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
) -> dict[str, Any]:
    """Apply approved operations (subset allowed)."""
    results: list[dict[str, Any]] = []
    for op in operations:
        conn = _connector_for(op, gmail, calendar, notion, obsidian)
        diff = _op_to_diff(op)
        try:
            out = await conn.apply_diff(diff)
            results.append({"id": op.id, "connector": op.connector.value, "status": "ok", "result": out})
            if audit:
                audit.log_execution(
                    connector=op.connector,
                    operation=op.operation,
                    payload=op.payload,
                    payload_summary=op.preview[:500],
                    target_id=op.target_id,
                    tool_operation_id=op.id,
                )
        except Exception as e:
            results.append(
                {"id": op.id, "connector": op.connector.value, "status": "error", "error": str(e)}
            )
    return {"executed": results}
