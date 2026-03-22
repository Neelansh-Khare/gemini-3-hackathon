"""Seeded demo data for all four connectors (mock mode)."""

from datetime import datetime, timedelta, timezone

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
