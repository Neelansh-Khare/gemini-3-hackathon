"""Executor agent: turns an approved plan into concrete ToolOperations (no writes)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from google import genai
from google.genai import types

from ...diff.generate_diffs import merge_planner_raw_ops, tool_ops_from_plan
from ...domain.prd_models import CandidatePlan, ConnectorName, OperationKind, ToolOperation
from .prompts import AGENT_PROMPTS


def tool_operations_deterministic(plan: CandidatePlan) -> list[ToolOperation]:
    return tool_ops_from_plan(plan)


def tool_operations_from_llm(
    api_key: str,
    plan: CandidatePlan,
    context_summary: str,
    model: str = "gemini-2.0-flash",
) -> list[ToolOperation]:
    """Ask Gemini for concrete tool_operations with payloads (still approval-gated)."""
    client = genai.Client(api_key=api_key)
    prompt = f"""Context summary:\n{context_summary}\n\nPlan JSON:\n{plan.model_dump_json()}\n\n{AGENT_PROMPTS['executor']}"""
    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
    )
    response = client.models.generate_content(model=model, contents=prompt, config=config)
    text = response.text or "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return tool_operations_deterministic(plan)
    raw = data.get("tool_operations") or data.get("diffs") or []
    if not raw:
        return tool_operations_deterministic(plan)
    normalized: list[dict[str, Any]] = []
    for r in raw:
        if "connector" not in r and "system" in r:
            r = {**r, "connector": r["system"]}
        normalized.append(r)
    return merge_planner_raw_ops(normalized)


def enrich_operations_with_payloads(
    plan: CandidatePlan,
    ops: list[ToolOperation],
    context_snippets: dict[str, str],
) -> list[ToolOperation]:
    """Attach richer preview payloads for mock execution (deterministic)."""
    gmail_ctx = context_snippets.get("gmail", "")
    out: list[ToolOperation] = []
    for op in ops:
        pl = dict(op.payload)
        preview = op.preview
        
        if op.connector == ConnectorName.GMAIL and op.operation == OperationKind.DRAFT:
            subject = pl.get("subject") or "Re: Q1 roadmap — priorities"
            pl.setdefault("subject", subject)
            pl.setdefault(
                "body",
                f"Hi — thanks for the nudge. Here are my top priorities for next week:\n"
                f"1) Life OS demo\n2) Product review prep\n3) Team follow-ups\n\nContext ref: {gmail_ctx[:120]}",
            )
            pl.setdefault("thread_id", "th_alex_q1")
            preview = f"Gmail: Draft reply '{subject}'"
            
        elif op.connector == ConnectorName.CALENDAR and op.operation == OperationKind.CREATE:
            title = pl.get("title") or "Deep work block"
            pl.setdefault("title", title)
            pl.setdefault("location", "Focus")
            preview = f"Calendar: Create event '{title}'"
            
        elif op.connector == ConnectorName.NOTION:
            title = pl.get("title") or "Weekly plan line"
            pl.setdefault("title", title)
            pl.setdefault("text", f"Aligned with plan: {plan.title}")
            pl.setdefault("type", "weekly_plan")
            preview = f"Notion: Append '{title}' to Weekly Plan"
            
        elif op.connector == ConnectorName.OBSIDIAN:
            path = pl.get("path") or "journal/2025-03.md"
            pl.setdefault("path", path)
            pl.setdefault("section", "## Weekly plan")
            pl.setdefault("body", f"- {plan.summary}\n")
            preview = f"Obsidian: Append plan to {path}"
            
        new_id = op.id or str(uuid.uuid4())
        out.append(
            ToolOperation(
                id=new_id,
                connector=op.connector,
                operation=op.operation,
                target_id=op.target_id,
                preview=preview[:500],
                payload=pl,
                requires_approval=True,
            )
        )
    return out
