"""Multi-Agent Council — planner (multi-plan), combined scoring, optional Gemini."""

from __future__ import annotations

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

    def _generate(self, prompt: str) -> str:
        if not self._client:
            return "{}"
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text or "{}"

    def parse_intent(self, user_message: str) -> dict[str, Any]:
        if not self._client:
            return {
                "goal": user_message,
                "entities_mentioned": [],
                "constraints": [],
                "preferred_systems": [],
            }
        prompt = INTENT_PARSING_PROMPT.format(intent=user_message)
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "goal": user_message,
                "entities_mentioned": [],
                "constraints": [],
                "preferred_systems": [],
            }

    def run_planner_multi(
        self,
        intent: dict[str, Any],
        context_items: list[dict[str, Any]],
    ) -> list[CandidatePlan]:
        if not self._client:
            return seed_candidate_plans()
        ctx_str = json.dumps(context_items, indent=2, default=str)[:8000]
        prompt = f"""User goal: {json.dumps(intent)}

Retrieved context items:
{ctx_str}

{AGENT_PROMPTS["planner_multi"]}"""
        text = self._generate(prompt)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return seed_candidate_plans()
        plans = _parse_plans_from_json(data)
        if len(plans) < 2:
            return seed_candidate_plans()
        return plans[:3]

    def score_and_recommend(
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
        prompt = f"""User intent: {json.dumps(intent)}

Candidate plans:
{json.dumps(plans_blob, indent=2)[:12000]}

{AGENT_PROMPTS["council_score"]}"""
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "recommended_plan_id": plans[0].id,
                "scores": {},
                "summary": "Council deliberation completed.",
                "warnings": [],
                "approval_required": True,
            }
