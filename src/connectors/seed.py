"""Seeded demo data for all four connectors (mock mode)."""

from datetime import datetime, timedelta, timezone

from ..lifegraph.schema import Task, Goal, Project, Person, Communication, Relation, RelationType
from ..lifegraph.storage import LifeGraphStorage

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def seed_gmail_threads() -> list[dict]:
    return [
        {
            "id": "th_alex_q1",
            "subject": "Q1 roadmap — need your input",
            "from": "Alex Rivera <alex@example.com>",
            "snippet": "Hey — can you reply with priorities for next week? Blocking the exec review.",
            "unread": True,
            "labels": ["INBOX", "IMPORTANT"],
            "internal_date": _now() - timedelta(hours=18),
        },
        {
            "id": "th_newsletter",
            "subject": "Weekly digest",
            "from": "Digest <news@example.com>",
            "snippet": "Top stories this week...",
            "unread": False,
            "labels": ["INBOX"],
            "internal_date": _now() - timedelta(days=2),
        },
    ]


def seed_gmail_drafts() -> list[dict]:
    return []


def seed_calendar_events() -> list[dict]:
    base = _now().replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        {
            "id": "ev_standup",
            "title": "Team standup",
            "start": base + timedelta(days=1, hours=1),
            "end": base + timedelta(days=1, hours=1, minutes=30),
            "location": "Zoom",
        },
        {
            "id": "ev_1on1",
            "title": "1:1 with manager",
            "start": base + timedelta(days=2, hours=15),
            "end": base + timedelta(days=2, hours=15, minutes=45),
            "location": "Office / B12",
        },
        {
            "id": "ev_review",
            "title": "Product review",
            "start": base + timedelta(days=4, hours=14),
            "end": base + timedelta(days=4, hours=15),
            "location": "Calendar hold",
        },
    ]


def seed_notion_items() -> list[dict]:
    return [
        {
            "id": "ng_weekly",
            "type": "goal",
            "title": "Ship MVP demo video",
            "status": "in progress",
            "due": (_now() + timedelta(days=5)).date().isoformat(),
        },
        {
            "id": "nt_followup",
            "type": "task",
            "title": "Follow up with Alex on Q1 priorities",
            "status": "todo",
            "due": (_now() + timedelta(days=1)).date().isoformat(),
        },
        {
            "id": "nt_workout",
            "type": "task",
            "title": "3× workouts this week",
            "status": "todo",
            "due": None,
        },
    ]


def seed_obsidian_notes() -> list[dict]:
    return [
        {
            "path": "journal/2025-03.md",
            "title": "March reflection",
            "body": "## Wins\n- Started Life OS prototype\n\n## Focus next week\n- Meetings Mon/Wed\n- Deep work Tue/Thu AM",
        },
        {
            "path": "projects/life-os.md",
            "title": "Life OS",
            "body": "## Principles\n- Human-in-the-loop\n- Append-only by default\n",
        },
    ]


def seed_lifegraph(storage: LifeGraphStorage) -> None:
    """Seed LifeGraph with entities and relations."""
    now = _now()
    
    # 1. Create entities
    p1 = Project(
        id="proj_life_os",
        title="Life OS MVP",
        description="Personal control plane prototype",
        created_at=now - timedelta(days=10),
        updated_at=now,
        status="active"
    )
    g1 = Goal(
        id="goal_mvp_demo",
        title="Ship MVP demo video",
        description="Record and edit a 2-min demo",
        created_at=now - timedelta(days=5),
        updated_at=now,
        status="in_progress",
        priority=1
    )
    t1 = Task(
        id="task_alex_followup",
        title="Follow up with Alex on Q1 priorities",
        description="Check email thread th_alex_q1",
        created_at=now - timedelta(days=1),
        updated_at=now,
        status="todo"
    )
    t2 = Task(
        id="task_workout",
        title="3x workouts this week",
        created_at=now - timedelta(days=3),
        updated_at=now,
        status="todo"
    )
    person1 = Person(
        id="person_alex",
        title="Alex Rivera",
        email="alex@example.com",
        created_at=now - timedelta(days=30),
        updated_at=now
    )
    comm1 = Communication(
        id="comm_alex_q1",
        title="Q1 roadmap email",
        source_system="gmail",
        source_id="th_alex_q1",
        created_at=now - timedelta(hours=18),
        updated_at=now - timedelta(hours=18)
    )

    # Save entities
    storage.save_entity(p1)
    storage.save_entity(g1)
    storage.save_entity(t1)
    storage.save_entity(t2)
    storage.save_entity(person1)
    storage.save_entity(comm1)

    # 2. Create relations
    storage.save_relation(Relation(
        source_id=g1.id,
        target_id=p1.id,
        relation_type=RelationType.PART_OF,
        created_at=now
    ))
    storage.save_relation(Relation(
        source_id=t1.id,
        target_id=g1.id,
        relation_type=RelationType.DEPENDS_ON,
        created_at=now
    ))
    storage.save_relation(Relation(
        source_id=t1.id,
        target_id=person1.id,
        relation_type=RelationType.MENTIONS,
        created_at=now
    ))
    storage.save_relation(Relation(
        source_id=comm1.id,
        target_id=person1.id,
        relation_type=RelationType.MENTIONS,
        created_at=now
    ))
    storage.save_relation(Relation(
        source_id=t1.id,
        target_id=comm1.id,
        relation_type=RelationType.REFERENCES,
        created_at=now
    ))
