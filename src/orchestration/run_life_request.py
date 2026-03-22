"""Central orchestration: intent → connectors → context → council → executor preview."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..diff.generate_diffs import tool_ops_from_plan
from ..domain.prd_models import CandidatePlan, ToolOperation
from ..retrieval.context_assembler import assemble_context
from .agents.council import AgentCouncil
from .agents.executor_agent import enrich_operations_with_payloads, tool_operations_from_llm
from .mock_plans import seed_candidate_plans

if TYPE_CHECKING:
    from ..connectors.calendar import CalendarConnector
    from ..connectors.gmail import GmailConnector
    from ..connectors.notion import NotionConnector
    from ..connectors.obsidian import ObsidianConnector


def _pick_plan(plans: list[CandidatePlan], recommended_id: str | None) -> CandidatePlan:
    if not plans:
        return seed_candidate_plans()[0]
    if recommended_id:
        for p in plans:
            if p.id == recommended_id:
                return p
    for p in plans:
        if p.id == "plan-balanced":
            return p
    return plans[0]


async def run_life_request(
    user_intent: str,
    council: AgentCouncil,
    gmail: GmailConnector,
    calendar: CalendarConnector,
    notion: NotionConnector,
    obsidian: ObsidianConnector,
    *,
    use_llm_executor: bool = True,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash",
) -> dict[str, Any]:
    """Full pipeline for POST /intent."""
    intent = council.parse_intent(user_intent)
    packet = assemble_context(user_intent, gmail, calendar, notion, obsidian)
    ctx_items = [i.model_dump(mode="json") for i in packet.items]

    plans = council.run_planner_multi(intent, ctx_items)
    rec = council.score_and_recommend(plans, intent)
    chosen = _pick_plan(plans, rec.get("recommended_plan_id"))

    context_snippets = {
        "gmail": next((i.body for i in packet.items if i.source.value == "gmail"), ""),
        "summary": packet.summary,
    }

    if use_llm_executor and gemini_api_key:
        tool_ops = tool_operations_from_llm(
            gemini_api_key,
            chosen,
            packet.summary + "\n" + "\n".join(x.body[:400] for x in packet.items[:6]),
            model=gemini_model,
        )
    else:
        tool_ops = tool_ops_from_plan(chosen)

    tool_ops = enrich_operations_with_payloads(chosen, tool_ops, context_snippets)

    return {
        "goal": intent.get("goal", user_intent),
        "intent": intent,
        "context_packet": packet.model_dump(mode="json"),
        "candidate_plans": [p.model_dump(mode="json") for p in plans],
        "recommended_plan_id": chosen.id,
        "recommended_plan": chosen.model_dump(mode="json"),
        "council_recommendation": rec,
        "tool_operations": [t.model_dump(mode="json") for t in tool_ops],
        "approval_required": True,
        "summary": rec.get("summary", chosen.summary),
        "warnings": list(rec.get("warnings") or []),
    }
