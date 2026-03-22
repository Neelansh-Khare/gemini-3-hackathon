"""Deterministic candidate plans when LLM is unavailable (demo-safe)."""

from ..domain.prd_models import CandidatePlan, EstimatedEffort, PlanStep, PlanStepType, TargetSystem


def seed_candidate_plans() -> list[CandidatePlan]:
    return [
        CandidatePlan(
            id="plan-balanced",
            title="Balanced week",
            summary="Spread deep work, workouts, and follow-ups across the week with buffer around meetings.",
            steps=[
                PlanStep(
                    type=PlanStepType.SCHEDULE,
                    description="Block Tue/Thu 8–11am for deep work; keep Mon standup + Wed 1:1 as anchors.",
                    target_system=TargetSystem.CALENDAR,
                    priority=1,
                ),
                PlanStep(
                    type=PlanStepType.TASK,
                    description="Add three workout blocks + link to Notion weekly goals.",
                    target_system=TargetSystem.NOTION,
                    priority=2,
                ),
                PlanStep(
                    type=PlanStepType.COMMUNICATION,
                    description="Draft reply to Alex on Q1 priorities (no send — draft only).",
                    target_system=TargetSystem.GMAIL,
                    priority=3,
                ),
                PlanStep(
                    type=PlanStepType.NOTE_UPDATE,
                    description="Append weekly plan bullets to journal/2025-03.md.",
                    target_system=TargetSystem.OBSIDIAN,
                    priority=4,
                ),
            ],
            risks=["Slight context switching if meetings overrun."],
            benefits=["Clear focus windows", "Inbox unblocked", "Goals visible in Notion"],
            estimated_effort=EstimatedEffort.MEDIUM,
        ),
        CandidatePlan(
            id="plan-aggressive",
            title="Deadline-first",
            summary="Front-load exec-critical work and Alex follow-up; compress workouts.",
            steps=[
                PlanStep(
                    type=PlanStepType.COMMUNICATION,
                    description="Draft detailed reply to Alex today with three bullet priorities.",
                    target_system=TargetSystem.GMAIL,
                    priority=1,
                ),
                PlanStep(
                    type=PlanStepType.TASK,
                    description="Mark 'Ship MVP demo' as top priority; move secondary tasks to next week in Notion.",
                    target_system=TargetSystem.NOTION,
                    priority=2,
                ),
                PlanStep(
                    type=PlanStepType.SCHEDULE,
                    description="Protect Thu PM for product review prep.",
                    target_system=TargetSystem.CALENDAR,
                    priority=3,
                ),
            ],
            risks=["Burnout if deep work blocks slip.", "Fewer workout slots."],
            benefits=["Fast unblock on Q1", "Review readiness"],
            estimated_effort=EstimatedEffort.HIGH,
        ),
        CandidatePlan(
            id="plan-recovery",
            title="Sustainable rhythm",
            summary="Prioritize sleep and movement; lighter week with minimal new calendar holds.",
            steps=[
                PlanStep(
                    type=PlanStepType.SCHEDULE,
                    description="Only add soft holds — no new hard meetings.",
                    target_system=TargetSystem.CALENDAR,
                    priority=1,
                ),
                PlanStep(
                    type=PlanStepType.TASK,
                    description="Keep 3× workouts as stretch goals in Notion (non-blocking).",
                    target_system=TargetSystem.NOTION,
                    priority=2,
                ),
                PlanStep(
                    type=PlanStepType.NOTE_UPDATE,
                    description="Short reflection in Obsidian on energy and constraints.",
                    target_system=TargetSystem.OBSIDIAN,
                    priority=3,
                ),
            ],
            risks=["Alex thread may wait longer."],
            benefits=["Lower stress", "Movement preserved"],
            estimated_effort=EstimatedEffort.LOW,
        ),
    ]
