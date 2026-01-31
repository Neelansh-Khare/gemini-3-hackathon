"""Core orchestration flow: intent → retrieve → deliberate → plan → approve → execute."""

from typing import Any

from ..lifegraph.schema import Entity
from ..lifegraph.storage import LifeGraphStorage
from ..retrieval.hybrid import HybridRetriever
from .agents.council import AgentCouncil


async def orchestrate(
    user_intent: str,
    council: AgentCouncil,
    retriever: HybridRetriever,
    storage: LifeGraphStorage,
    require_approval: bool = True,
) -> dict[str, Any]:
    """Full orchestration flow. Returns plan + diffs for user approval.

    Flow:
    1. Parse intent
    2. Retrieve context
    3. Planner produces plan
    4. Skeptic, Optimizer, Privacy score
    5. Recommendation with diffs
    6. approval_required=True → user must approve before execute
    """
    # 1. Parse intent
    intent = council.parse_intent(user_intent)

    # 2. Retrieve context
    context_entities = retriever.get_context_for_intent(user_intent, top_k=15)
    context = [e.model_dump() for e in context_entities]

    # 3. Planner produces plan
    plan = council.run_planner(intent, context)

    # 4. Council deliberation
    skeptic = council.run_skeptic(plan)
    optimizer = council.run_optimizer(plan)
    privacy = council.run_privacy(plan)

    # 5. Recommendation
    recommendation = council.recommend_plan(plan, skeptic, optimizer, privacy)

    # 6. Build response (orchestrator output schema from PRD)
    return {
        "goal": intent.get("goal", user_intent),
        "candidate_plans": [plan],
        "recommended_plan": recommendation.get("recommended_plan"),
        "diffs": plan.get("diffs", []),
        "approval_required": require_approval or recommendation.get("approval_required", True),
        "summary": recommendation.get("summary", plan.get("summary", "")),
        "warnings": recommendation.get("warnings", []),
        "council_scores": {
            "skeptic": skeptic.get("score"),
            "optimizer": optimizer.get("score"),
            "privacy": privacy.get("score"),
        },
    }


async def execute_approved(
    diffs: list[dict[str, Any]],
    connectors: list[Any],
) -> dict[str, Any]:
    """Execute approved diffs via write-back connectors.

    Each diff has: system, operation, target, payload.
    Routes to appropriate connector.
    """
    results: list[dict[str, Any]] = []
    for diff in diffs:
        system = diff.get("system", "")
        for conn in connectors:
            if conn.can_handle(system):
                try:
                    result = await conn.apply_diff(diff)
                    results.append({"system": system, "status": "ok", "result": result})
                except Exception as e:
                    results.append({"system": system, "status": "error", "error": str(e)})
                break
        else:
            results.append({"system": system, "status": "no_connector", "error": f"No connector for {system}"})
    return {"executed": results}
