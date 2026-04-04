"""Turn approved plans into concrete ToolOperation previews (no execution)."""

from __future__ import annotations

import uuid
from typing import Any

from ..domain.prd_models import (
    CandidatePlan,
    ConnectorName,
    OperationKind,
    PlanStepType,
    ToolOperation,
)


def _connector_for_step(step_type: PlanStepType, target: str) -> ConnectorName:
    t = target.lower()
    if "gmail" in t:
        return ConnectorName.GMAIL
    if "calendar" in t or "cal" in t:
        return ConnectorName.CALENDAR
    if "notion" in t:
        return ConnectorName.NOTION
    if "obsidian" in t or "obs" in t:
        return ConnectorName.OBSIDIAN
    if step_type == PlanStepType.SCHEDULE:
        return ConnectorName.CALENDAR
    if step_type == PlanStepType.COMMUNICATION:
        return ConnectorName.GMAIL
    if step_type == PlanStepType.NOTE_UPDATE:
        return ConnectorName.OBSIDIAN
    return ConnectorName.NOTION


def _operation_for_step(step_type: PlanStepType) -> OperationKind:
    if step_type == PlanStepType.COMMUNICATION:
        return OperationKind.DRAFT
    if step_type == PlanStepType.NOTE_UPDATE:
        return OperationKind.APPEND
    return OperationKind.CREATE


def tool_ops_from_plan(plan: CandidatePlan) -> list[ToolOperation]:
    """Deterministic tool ops from structured candidate plan steps."""
    ops: list[ToolOperation] = []
    for step in plan.steps:
        cid = _connector_for_step(step.type, step.target_system.value)
        op = _operation_for_step(step.type)
        
        # Enhanced descriptive preview
        if cid == ConnectorName.CALENDAR:
            preview = f"Calendar: Schedule '{step.description}'"
        elif cid == ConnectorName.GMAIL:
            preview = f"Gmail: Draft reply for '{step.description}'"
        elif cid == ConnectorName.NOTION:
            preview = f"Notion: Add task '{step.description}'"
        elif cid == ConnectorName.OBSIDIAN:
            preview = f"Obsidian: Log note '{step.description}'"
        else:
            preview = f"[{cid.value}] {op.value}: {step.description}"
            
        payload: dict[str, Any] = {
            "step_type": step.type.value,
            "target_system": step.target_system.value,
            "priority": step.priority,
            "description": step.description,
        }
        ops.append(
            ToolOperation(
                id=str(uuid.uuid4()),
                connector=cid,
                operation=op,
                target_id=None,
                preview=preview,
                payload=payload,
                requires_approval=True,
            )
        )
    return ops


def merge_planner_raw_ops(raw_ops: list[dict[str, Any]]) -> list[ToolOperation]:
    """Map planner JSON tool_ops / diffs into ToolOperation models."""
    out: list[ToolOperation] = []
    for r in raw_ops:
        conn_s = (r.get("connector") or r.get("system") or "notion").lower()
        try:
            connector = ConnectorName(conn_s)
        except ValueError:
            connector = ConnectorName.NOTION
        op_s = (r.get("operation") or "create").lower()
        try:
            operation = OperationKind(op_s)
        except ValueError:
            operation = OperationKind.CREATE
        out.append(
            ToolOperation(
                id=r.get("id") or str(uuid.uuid4()),
                connector=connector,
                operation=operation,
                target_id=r.get("target_id"),
                preview=r.get("preview") or r.get("summary") or str(r.get("payload", ""))[:300],
                payload=r.get("payload") if isinstance(r.get("payload"), dict) else {},
                requires_approval=r.get("requires_approval", True),
            )
        )
    return out
