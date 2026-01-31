"""FastAPI routes for Life OS orchestrator."""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import settings
from src.lifegraph.storage import LifeGraphStorage
from src.lifegraph.graph import LifeGraph
from src.retrieval.hybrid import HybridRetriever
from src.orchestration.flows import orchestrate, execute_approved
from src.orchestration.agents.council import AgentCouncil

app = FastAPI(
    title="Life OS",
    description="Personal control plane that reasons across your life and safely executes decisions",
    version="0.1.0",
)


# --- Request/Response schemas ---


class IntentRequest(BaseModel):
    intent: str


class ApproveRequest(BaseModel):
    diffs: list[dict[str, Any]]


# --- Lazy init (depends on settings) ---


def _get_council() -> AgentCouncil:
    if not settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY not configured")
    return AgentCouncil(api_key=settings.gemini_api_key, model=settings.gemini_model)


def _get_graph() -> LifeGraph:
    storage = LifeGraphStorage(settings.lifegraph_db)
    return storage.load()


def _get_retriever() -> HybridRetriever:
    graph = _get_graph()
    return HybridRetriever(graph, settings.vector_store_path)


def _get_storage() -> LifeGraphStorage:
    return LifeGraphStorage(settings.lifegraph_db)


# --- Routes ---


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "life-os"}


@app.post("/intent", response_model=dict[str, Any])
async def handle_intent(req: IntentRequest) -> dict[str, Any]:
    """Main entry: user states intent → returns plan + diffs for approval."""
    council = _get_council()
    retriever = _get_retriever()
    storage = _get_storage()
    result = await orchestrate(
        user_intent=req.intent,
        council=council,
        retriever=retriever,
        storage=storage,
        require_approval=settings.require_approval_for_writes,
    )
    return result


@app.post("/approve", response_model=dict[str, Any])
async def approve_and_execute(req: ApproveRequest) -> dict[str, Any]:
    """Execute approved diffs. Connectors must be registered (MVP: stub)."""
    # TODO: Register connectors (GmailWriter, CalendarWriter, etc.)
    connectors: list[Any] = []
    result = await execute_approved(diffs=req.diffs, connectors=connectors)
    return result
