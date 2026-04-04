"""FastAPI routes for Life OS orchestrator."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from src.audit.audit_log import AuditLog
from src.connectors.registry import mock_connectors
from src.domain.prd_models import ToolOperation
from src.orchestration.agents.council import AgentCouncil
from src.orchestration.flows import execute_tool_operations, rollback_tool_operations
from src.orchestration.run_life_request import run_life_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    g, cal, n, ob = mock_connectors()
    app.state.gmail = g
    app.state.calendar = cal
    app.state.notion = n
    app.state.obsidian = ob
    app.state.audit = AuditLog(settings.audit_db)
    yield


app = FastAPI(
    title="Life OS",
    description="Personal control plane — context, council, approval-gated writes",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IntentRequest(BaseModel):
    intent: str


class ApproveRequest(BaseModel):
    """Execute a user-approved subset of tool operations."""

    tool_operations: list[ToolOperation]


class RollbackRequest(BaseModel):
    """Undo specific audit log entries."""

    entry_ids: list[str]


def _council() -> AgentCouncil:
    key = settings.gemini_api_key.strip() or None
    return AgentCouncil(api_key=key, model=settings.gemini_model)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "life-os"}


@app.post("/intent", response_model=dict[str, Any])
async def handle_intent(req: IntentRequest, request: Request) -> dict[str, Any]:
    """User request → context from all connectors → candidate plans → tool op previews."""
    council = _council()
    st = request.app.state
    key = settings.gemini_api_key.strip() or None
    return await run_life_request(
        req.intent,
        council,
        st.gmail,
        st.calendar,
        st.notion,
        st.obsidian,
        use_llm_executor=bool(key),
        gemini_api_key=key,
        gemini_model=settings.gemini_model,
    )


@app.post("/approve", response_model=dict[str, Any])
async def approve_and_execute(req: ApproveRequest, request: Request) -> dict[str, Any]:
    """Execute approved tool operations (writes) and append audit log."""
    if not req.tool_operations:
        raise HTTPException(400, "tool_operations required")
    st = request.app.state
    return await execute_tool_operations(
        req.tool_operations,
        st.gmail,
        st.calendar,
        st.notion,
        st.obsidian,
        audit=st.audit,
    )


@app.post("/rollback", response_model=dict[str, Any])
async def rollback_entries(req: RollbackRequest, request: Request) -> dict[str, Any]:
    """Undo specific audit log entries."""
    if not req.entry_ids:
        raise HTTPException(400, "entry_ids required")
    st = request.app.state
    return await rollback_tool_operations(
        req.entry_ids,
        st.gmail,
        st.calendar,
        st.notion,
        st.obsidian,
        audit=st.audit,
    )


@app.get("/audit", response_model=dict[str, Any])
async def list_audit(request: Request, limit: int = 100) -> dict[str, Any]:
    entries = request.app.state.audit.list_recent(limit=limit)
    return {"entries": [e.model_dump(mode="json") for e in entries]}


@app.post("/demo/reset", response_model=dict[str, str])
async def reset_demo(request: Request) -> dict[str, str]:
    """Reset in-memory mock connectors (demo / screen recording)."""
    st = request.app.state
    st.gmail.reset()
    st.calendar.reset()
    st.notion.reset()
    st.obsidian.reset()
    return {"status": "reset"}
