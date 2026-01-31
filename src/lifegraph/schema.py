"""LifeGraph entity types and relationship schema.

Entities: People, Projects, Goals, Tasks, Events, Decisions
Relations: depends_on, scheduled_for, relates_to, blocks
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(StrEnum):
    """Canonical entity types in the LifeGraph."""

    PERSON = "person"
    PROJECT = "project"
    GOAL = "goal"
    TASK = "task"
    EVENT = "event"
    DECISION = "decision"


class RelationType(StrEnum):
    """Relationship types between entities."""

    DEPENDS_ON = "depends_on"
    SCHEDULED_FOR = "scheduled_for"
    RELATES_TO = "relates_to"
    BLOCKS = "blocks"
    ASSIGNED_TO = "assigned_to"
    PART_OF = "part_of"


# --- Base Entity ---


class Entity(BaseModel):
    """Base entity with common fields. All LifeGraph nodes extend this."""

    id: str = Field(..., description="Unique identifier")
    type: EntityType = Field(..., description="Entity type")
    title: str = Field(..., description="Human-readable title")
    description: str | None = Field(default=None, description="Optional description")
    source_system: str | None = Field(default=None, description="Origin: gmail, notion, calendar, obsidian")
    source_id: str | None = Field(default=None, description="ID in source system")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Concrete Entity Types ---


class Person(Entity):
    """A person in the user's life (contact, collaborator)."""

    type: EntityType = Field(default=EntityType.PERSON, init=False)
    email: str | None = None


class Project(Entity):
    """A project (workstream, initiative)."""

    type: EntityType = Field(default=EntityType.PROJECT, init=False)
    status: str = "active"


class Goal(Entity):
    """A goal with optional deadline."""

    type: EntityType = Field(default=EntityType.GOAL, init=False)
    deadline: datetime | None = None
    progress: float = 0.0


class Task(Entity):
    """A task (todo, action item)."""

    type: EntityType = Field(default=EntityType.TASK, init=False)
    status: str = "pending"  # pending, in_progress, done, cancelled
    due_at: datetime | None = None
    priority: str = "medium"  # low, medium, high


class Event(Entity):
    """A calendar event or appointment."""

    type: EntityType = Field(default=EntityType.EVENT, init=False)
    start_at: datetime | None = None
    end_at: datetime | None = None
    location: str | None = None


class Decision(Entity):
    """A decision made or to be made."""

    type: EntityType = Field(default=EntityType.DECISION, init=False)
    outcome: str | None = None  # Once decided
    decided_at: datetime | None = None


# --- Relation ---


class Relation(BaseModel):
    """Directed edge between two entities."""

    source_id: str = Field(..., description="ID of source entity")
    target_id: str = Field(..., description="ID of target entity")
    relation_type: RelationType = Field(..., description="Type of relationship")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
