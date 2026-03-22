"""Strong domain models aligned with the Life OS PRD (Pydantic, zod-equivalent)."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanStepType(StrEnum):
    SCHEDULE = "schedule"
    TASK = "task"
    COMMUNICATION = "communication"
    NOTE_UPDATE = "note_update"


class TargetSystem(StrEnum):
    CALENDAR = "calendar"
    NOTION = "notion"
    GMAIL = "gmail"
    OBSIDIAN = "obsidian"


class EstimatedEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlanStep(BaseModel):
    type: PlanStepType
    description: str
    target_system: TargetSystem
    priority: int = Field(default=1, ge=1, le=10)


class CandidatePlan(BaseModel):
    id: str
    title: str
    summary: str
    steps: list[PlanStep] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    estimated_effort: EstimatedEffort = EstimatedEffort.MEDIUM


class PlanEvaluation(BaseModel):
    plan_id: str
    skeptic_score: float | None = None
    optimizer_score: float | None = None
    privacy_score: float | None = None
    combined_notes: str = ""


class ConnectorName(StrEnum):
    GMAIL = "gmail"
    CALENDAR = "calendar"
    NOTION = "notion"
    OBSIDIAN = "obsidian"


class OperationKind(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    APPEND = "append"
    DRAFT = "draft"


class ToolOperation(BaseModel):
    id: str
    connector: ConnectorName
    operation: OperationKind
    target_id: str | None = None
    preview: str
    payload: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = True


class ContextItem(BaseModel):
    """Single retrieved item after normalization."""

    id: str
    source: ConnectorName
    kind: str
    title: str
    body: str
    occurred_at: datetime | None = None
    relevance: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextPacket(BaseModel):
    query: str
    items: list[ContextItem] = Field(default_factory=list)
    summary: str = ""
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED_ALL = "approved_all"
    REJECTED_ALL = "rejected_all"
    PARTIAL = "partial"


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    connector: ConnectorName
    operation: OperationKind
    target_id: str | None = None
    payload_summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    tool_operation_id: str | None = None
