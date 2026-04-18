"""Multi-Agent Council — planner (multi-plan), combined scoring, optional Gemini."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from google import genai
from google.genai import types

from ...domain.prd_models import CandidatePlan, EstimatedEffort, PlanStep, PlanStepType, TargetSystem
from ..mock_plans import seed_candidate_plans
from .prompts import AGENT_PROMPTS, INTENT_PARSING_PROMPT


def _parse_plans_from_json(data: dict[str, Any]) -> list[CandidatePlan]:
    raw_plans = data.get("plans") or []
    out: list[CandidatePlan] = []
    for p in raw_plans:
        try:
            steps: list[PlanStep] = []
            for s in p.get("steps") or []:
                st = str(s.get("type", "task")).lower()
                type_map = {
                    "schedule": PlanStepType.SCHEDULE,
                    "task": PlanStepType.TASK,
                    "communication": PlanStepType.COMMUNICATION,
                    "note_update": PlanStepType.NOTE_UPDATE,
                }
                ts_raw = str(s.get("target_system", "notion")).lower()
                ts_map = {
                    "calendar": TargetSystem.CALENDAR,
                    "notion": TargetSystem.NOTION,
                    "gmail": TargetSystem.GMAIL,
                    "obsidian": TargetSystem.OBSIDIAN,
                }
                steps.append(
                    PlanStep(
                        type=type_map.get(st, PlanStepType.TASK),
                        description=s.get("description", ""),
                        target_system=ts_map.get(ts_raw, TargetSystem.NOTION),
                        priority=int(s.get("priority", 1)),
                    )
                )
            ef = str(p.get("estimated_effort", "medium")).lower()
            effort = EstimatedEffort.MEDIUM
            if ef in ("low", "medium", "high"):
                effort = EstimatedEffort(ef)
            out.append(
                CandidatePlan(
                    id=p.get("id", f"plan-{len(out)}"),
                    title=p.get("title", "Plan"),
                    summary=p.get("summary", ""),
                    steps=steps,
                    risks=list(p.get("risks") or []),
                    benefits=list(p.get("benefits") or []),
                    estimated_effort=effort,
                )
            )
        except Exception:
            continue
    return out


class AgentCouncil:
    """Planner, Skeptic, Optimizer, Privacy — Gemini never executes writes."""

    def __init__(self, api_key: str | None, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model
        self._client: genai.Client | None
        if api_key:
            self._client = genai.Client(api_key=api_key)
        else:
            self._client = None

    async def _generate(self, prompt: str) -> str:
        if not self._client:
            return "{}"
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text or "{}"

    async def parse_intent(self, user_message: str) -> dict[str, Any]:
        if not self._client:
            return {
                "goal": user_message,
                "entities_mentioned": [],
                "constraints": [],
                "preferred_systems": [],
            }
        prompt = INTENT_PARSING_PROMPT.format(intent=user_message)
        text = await self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "goal": user_message,
                "entities_mentioned": [],
                "constraints": [],
                "preferred_systems": [],
            }

    async def run_planner_multi(
        self,
        intent: dict[str, Any],
        context_items: list[dict[str, Any]],
    ) -> list[CandidatePlan]:
        """Produce 3 distinct plans (Balanced, Aggressive, Conservative) in parallel."""
        if not self._client:
            return seed_candidate_plans()
        
        ctx_str = json.dumps(context_items, indent=2, default=str)[:8000]
        
        strategies = [
            ("balanced", "A balanced approach minimizing risk while ensuring progress."),
            ("aggressive", "An aggressive, deadline-focused approach prioritizing speed and output."),
            ("conservative", "A conservative/recovery approach prioritizing safety, verification, and minimal impact."),
        ]
        
        async def get_plan(id_tag: str, strategy: str) -> list[CandidatePlan]:
            prompt = f"""User goal: {json.dumps(intent)}
Strategy: {strategy}
Retrieved context items:
{ctx_str}

{AGENT_PROMPTS["planner_single"]}
Produce exactly ONE plan with id 'plan-{id_tag}'.
"""
            text = await self._generate(prompt)
            try:
                data = json.loads(text)
                # If the LLM returns multiple plans, we just take the first one and ensure ID
                plans = _parse_plans_from_json(data)
                if plans:
                    plans[0].id = f"plan-{id_tag}"
                    return [plans[0]]
            except Exception:
                pass
            return []

        # Run strategies in parallel
        tasks = [get_plan(tag, strat) for tag, strat in strategies]
        results = await asyncio.gather(*tasks)
        
        all_plans: list[CandidatePlan] = []
        for r in results:
            all_plans.extend(r)
            
        if len(all_plans) < 2:
            return seed_candidate_plans()
        return all_plans[:3]

    async def score_and_recommend(
        self,
        plans: list[CandidatePlan],
        intent: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._client or len(plans) == 0:
            pick: CandidatePlan | None = None
            for p in plans or []:
                if p.id == "plan-balanced":
                    pick = p
                    break
            if not pick and plans:
                pick = plans[0]
            scores: dict[str, dict[str, float]] = {}
            for p in plans or []:
                scores[p.id] = {"skeptic": 7.0, "optimizer": 7.0, "privacy": 9.0}
            return {
                "recommended_plan_id": pick.id if pick else None,
                "scores": scores,
                "summary": "Offline council: seeded plans (balanced default when available).",
                "warnings": [],
                "approval_required": True,
            }

        plans_blob = [p.model_dump(mode="json") for p in plans]
        plans_json = json.dumps(plans_blob, indent=2)
        intent_json = json.dumps(intent)

        async def run_review(agent_key: str) -> dict[str, Any]:
            prompt = f"User intent: {intent_json}\n\nCandidate plans:\n{plans_json}\n\n{AGENT_PROMPTS[agent_key]}"
            res = await self._generate(prompt)
            try:
                return json.loads(res).get("scores", {})
            except Exception:
                return {}

        # Run reviews in parallel
        results = await asyncio.gather(
            run_review("skeptic"),
            run_review("optimizer"),
            run_review("privacy")
        )
        skeptic_data, optimizer_data, privacy_data = results

        # 4. Aggregate & Recommend (using a final summary call)
        reviews_summary = {
            "skeptic": skeptic_data,
            "optimizer": optimizer_data,
            "privacy": privacy_data
        }
        
        agg_prompt = f"""User intent: {intent_json}
Candidate plans: {plans_json}
Agent Reviews: {json.dumps(reviews_summary, indent=2)}

You are the Head of Council. Based on the Skeptic, Optimizer, and Privacy reviews, pick the best plan.
Provide a final summary and any critical warnings.

Output JSON:
{{
  "recommended_plan_id": "best plan id",
  "summary": "one line for the user explaining why this was picked",
  "warnings": ["any critical risks to highlight"],
  "approval_required": true
}}"""
        agg_res = await self._generate(agg_prompt)
        try:
            agg_data = json.loads(agg_res)
        except Exception:
            agg_data = {
                "recommended_plan_id": plans[0].id,
                "summary": "Council deliberation completed.",
                "warnings": [],
                "approval_required": True
            }

        # Combine scores for the UI
        final_scores = {}
        for p in plans:
            final_scores[p.id] = {
                "skeptic": skeptic_data.get(p.id, {}).get("score", 5.0),
                "optimizer": optimizer_data.get(p.id, {}).get("score", 5.0),
                "privacy": privacy_data.get(p.id, {}).get("score", 5.0)
            }
        
        agg_data["scores"] = final_scores
        # Also include detailed reviews for frontend if needed (future proofing)
        agg_data["reviews"] = reviews_summary
        
        return agg_data

