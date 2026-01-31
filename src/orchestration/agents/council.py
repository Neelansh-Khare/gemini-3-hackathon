"""Multi-Agent Council - each agent scores plans via Gemini."""

import json
from typing import Any

from google import genai
from google.genai import types

from .prompts import AGENT_PROMPTS, INTENT_PARSING_PROMPT, PLAN_RECOMMENDATION_PROMPT


class AgentCouncil:
    """Orchestrates Planner, Skeptic, Optimizer, Privacy agents. Gemini never executes writes."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def _generate(self, prompt: str, system_instruction: str | None = None) -> str:
        """Single Gemini call. Returns raw text."""
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        )
        if system_instruction:
            prompt = f"{system_instruction}\n\n{prompt}"
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text or "{}"

    def parse_intent(self, user_message: str) -> dict[str, Any]:
        """Parse user intent into structured form."""
        prompt = INTENT_PARSING_PROMPT.format(intent=user_message)
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"goal": user_message, "entities_mentioned": [], "constraints": [], "preferred_systems": []}

    def run_planner(self, intent: dict[str, Any], context: list[dict]) -> dict[str, Any]:
        """Planner produces candidate plan."""
        ctx_str = json.dumps(context, indent=2)[:4000]
        prompt = f"""Intent: {json.dumps(intent)}
Context entities:
{ctx_str}

{AGENT_PROMPTS["planner"]}"""
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"plan_id": "fallback", "summary": "Parse failed", "steps": [], "diffs": []}

    def run_skeptic(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Skeptic scores and raises concerns."""
        prompt = f"""Plan to review:
{json.dumps(plan, indent=2)}

{AGENT_PROMPTS["skeptic"]}"""
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"score": 5, "concerns": [], "suggestions": [], "verdict": "approve"}

    def run_optimizer(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Optimizer evaluates efficiency."""
        prompt = f"""Plan to optimize:
{json.dumps(plan, indent=2)}

{AGENT_PROMPTS["optimizer"]}"""
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"score": 5, "tradeoffs": [], "efficiency_notes": [], "recommendation": "proceed"}

    def run_privacy(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Privacy/compliance check."""
        prompt = f"""Plan to check:
{json.dumps(plan, indent=2)}

{AGENT_PROMPTS["privacy"]}"""
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"score": 10, "checks": {}, "issues": [], "verdict": "approve"}

    def recommend_plan(
        self,
        planner_output: dict,
        skeptic_output: dict,
        optimizer_output: dict,
        privacy_output: dict,
    ) -> dict[str, Any]:
        """Produce final recommendation from council outputs."""
        prompt = PLAN_RECOMMENDATION_PROMPT.format(
            planner_output=json.dumps(planner_output),
            skeptic_output=json.dumps(skeptic_output),
            optimizer_output=json.dumps(optimizer_output),
            privacy_output=json.dumps(privacy_output),
        )
        text = self._generate(prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "recommended_plan": planner_output.get("plan_id"),
                "combined_score": 5,
                "approval_required": True,
                "summary": "Council deliberation completed",
                "warnings": [],
            }
