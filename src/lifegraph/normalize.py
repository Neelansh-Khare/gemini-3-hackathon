"""Map connector-native records into LifeGraph entities."""

from datetime import datetime
from uuid import uuid4

from .schema import (
    Communication,
    Entity,
    Event,
    Goal,
    Note,
    Task,
)


def gmail_thread_to_entity(row: dict) -> Communication:
    return Communication(
        id=f"gmail:{row['id']}",
        title=row.get("subject", "(no subject)"),
        description=row.get("snippet", ""),
        source_system="gmail",
        source_id=row["id"],
        metadata={
            "from": row.get("from"),
            "labels": row.get("labels", []),
            "unread": row.get("unread", False),
        },
        thread_id=row["id"],
        is_draft=False,
    )


def gmail_draft_entity(row: dict) -> Communication:
    return Communication(
        id=f"gmail_draft:{row['id']}",
        title=row.get("subject", "Draft"),
        description=row.get("body", "")[:500],
        source_system="gmail",
        source_id=row["id"],
        metadata={"to": row.get("to"), "thread_id": row.get("thread_id")},
        thread_id=row.get("thread_id"),
        is_draft=True,
    )


def calendar_event_to_entity(row: dict) -> Event:
    return Event(
        id=f"cal:{row['id']}",
        title=row["title"],
        description=row.get("location"),
        source_system="calendar",
        source_id=row["id"],
        start_at=row["start"] if isinstance(row["start"], datetime) else None,
        end_at=row["end"] if isinstance(row["end"], datetime) else None,
        location=row.get("location"),
    )


def notion_item_to_entity(row: dict) -> Goal | Task:
    sid = row["id"]
    title = row["title"]
    desc = f"status={row.get('status')}, due={row.get('due')}"
    meta = {"notion_type": row.get("type"), "status": row.get("status")}
    if row.get("type") == "goal":
        return Goal(
            id=f"notion:{sid}",
            title=title,
            description=desc,
            source_system="notion",
            source_id=sid,
            metadata=meta,
        )
    return Task(
        id=f"notion:{sid}",
        title=title,
        description=desc,
        source_system="notion",
        source_id=sid,
        metadata=meta,
        status=row.get("status", "pending"),
    )


def obsidian_note_to_entity(row: dict) -> Note:
    path = row.get("path", "unknown.md")
    return Note(
        id=f"obsidian:{path}",
        title=row.get("title", path),
        description=row.get("body", "")[:2000],
        source_system="obsidian",
        source_id=path,
        path=path,
    )


def normalize_connector_record(source: str, record: dict) -> Entity | None:
    """Dispatch normalization by connector name."""
    if source == "gmail":
        if record.get("is_draft"):
            return gmail_draft_entity(record)
        return gmail_thread_to_entity(record)
    if source == "calendar":
        return calendar_event_to_entity(record)
    if source == "notion":
        return notion_item_to_entity(record)
    if source == "obsidian":
        return obsidian_note_to_entity(record)
    return None


def synthetic_entity_from_context_item(
    source: str, kind: str, title: str, body: str, eid: str | None = None
) -> Entity:
    """Fallback entity when structure is generic."""
    eid = eid or str(uuid4())
    prefix = f"{source}:{kind}:{eid}"
    if kind == "event":
        return Event(id=prefix, title=title, description=body, source_system=source)
    if kind in ("thread", "draft"):
        return Communication(
            id=prefix,
            title=title,
            description=body,
            source_system=source,
            is_draft=kind == "draft",
        )
    if kind == "note":
        return Note(id=prefix, title=title, description=body, source_system=source)
    if kind == "goal":
        return Goal(id=prefix, title=title, description=body, source_system=source)
    return Task(id=prefix, title=title, description=body, source_system=source)
