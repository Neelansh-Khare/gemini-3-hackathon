"""Fetch from connectors, normalize, rank into a compact ContextPacket."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..domain.prd_models import ConnectorName, ContextItem, ContextPacket

if TYPE_CHECKING:
    from ..connectors.calendar import CalendarConnector
    from ..connectors.gmail import GmailConnector
    from ..connectors.notion import NotionConnector
    from ..connectors.obsidian import ObsidianConnector


def _tokenize(q: str) -> set[str]:
    return {t.lower() for t in re.split(r"\W+", q) if len(t) > 2}


def _recency_score(dt: datetime | None) -> float:
    if not dt:
        return 0.4
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (datetime.now(timezone.utc) - dt).total_seconds()
    # decay: full score if < 1d, lower if older
    if delta < 86400:
        return 1.0
    if delta < 86400 * 7:
        return 0.75
    return 0.5


def _keyword_overlap(query: str, text: str) -> float:
    if not text:
        return 0.0
    qt = _tokenize(query)
    tt = _tokenize(text)
    if not qt:
        return 0.5
    inter = len(qt & tt)
    return min(1.0, inter / max(3, len(qt) * 0.5))


def assemble_context(
    user_query: str,
    gmail: GmailConnector,
    calendar: CalendarConnector,
    notion: NotionConnector,
    obsidian: ObsidianConnector,
    top_k: int = 24,
) -> ContextPacket:
    """Build ranked context from all four mock connectors with dynamic weighting."""
    items: list[ContextItem] = []
    
    # Detect intent to adjust weights
    q_lower = user_query.lower()
    time_sensitive = any(w in q_lower for w in ["next", "week", "today", "tomorrow", "deadline", "soon", "meeting", "schedule"])
    
    # Weights: Relevance, Importance, Recency
    if time_sensitive:
        w_rel, w_imp, w_rec = 0.35, 0.20, 0.45
    else:
        w_rel, w_imp, w_rec = 0.50, 0.30, 0.20

    for t in gmail.list_threads():
        body = f"{t.get('subject','')} {t.get('snippet','')} {t.get('from','')}"
        kw_score = _keyword_overlap(user_query, body)
        imp = 0.9 if t.get("unread") else 0.4
        if "IMPORTANT" in t.get("labels", []):
            imp = min(1.0, imp + 0.05)
        od = t.get("internal_date")
        occ = od if isinstance(od, datetime) else None
        
        rel = 0.5 * kw_score + 0.5 * imp
        reason = f"Keyword match: {kw_score:.0%}"
        if t.get("unread"):
            reason += " · Unread priority"
        
        items.append(
            ContextItem(
                id=f"gmail:{t['id']}",
                source=ConnectorName.GMAIL,
                kind="thread",
                title=t.get("subject", ""),
                body=t.get("snippet", ""),
                occurred_at=occ,
                relevance=min(1.0, rel),
                importance=imp,
                reasoning=reason,
                metadata={"from": t.get("from"), "unread": t.get("unread")},
            )
        )

    for e in calendar.list_events():
        body = f"{e.get('title','')} {e.get('location','')}"
        st = e.get("start")
        occ = st if isinstance(st, datetime) else None
        kw_score = _keyword_overlap(user_query, body)
        rec_score = _recency_score(occ)
        rel = 0.55 * kw_score + 0.45 * rec_score
        
        reason = f"Keyword match: {kw_score:.0%}"
        if rec_score > 0.8:
            reason += " · Recent event"
            
        items.append(
            ContextItem(
                id=f"cal:{e['id']}",
                source=ConnectorName.CALENDAR,
                kind="event",
                title=e.get("title", ""),
                body=str(e.get("location", "")),
                occurred_at=occ,
                relevance=rel,
                importance=0.7,
                reasoning=reason,
                metadata={"start": e.get("start"), "end": e.get("end")},
            )
        )

    for n in notion.list_items():
        body = f"{n.get('title','')} {n.get('status','')} {n.get('due','')}"
        kw_score = _keyword_overlap(user_query, body)
        type_boost = 0.85 if n.get("type") == "goal" else 0.65
        rel = kw_score * 0.7 + 0.3 * type_boost
        
        reason = f"Keyword match: {kw_score:.0%}"
        if n.get("type") == "goal":
            reason += " · High-level goal boost"

        items.append(
            ContextItem(
                id=f"notion:{n['id']}",
                source=ConnectorName.NOTION,
                kind=n.get("type", "task"),
                title=n.get("title", ""),
                body=body,
                occurred_at=None,
                relevance=min(1.0, rel),
                importance=0.8 if n.get("type") == "goal" else 0.6,
                reasoning=reason,
                metadata={"status": n.get("status"), "due": n.get("due")},
            )
        )

    for note in obsidian.list_notes():
        body = f"{note.get('title','')} {note.get('body','')}"
        kw_score = _keyword_overlap(user_query, body)
        rel = kw_score
        
        items.append(
            ContextItem(
                id=f"obs:{note['path']}",
                source=ConnectorName.OBSIDIAN,
                kind="note",
                title=note.get("title", note.get("path", "")),
                body=(note.get("body") or "")[:1500],
                occurred_at=None,
                relevance=min(1.0, rel + 0.15),
                importance=0.55,
                reasoning=f"Keyword match: {kw_score:.0%}",
                metadata={"path": note.get("path")},
            )
        )

    def sort_key(it: ContextItem) -> float:
        rec = _recency_score(it.occurred_at) if it.occurred_at else 0.55
        return w_rel * it.relevance + w_imp * it.importance + w_rec * rec

    items.sort(key=sort_key, reverse=True)
    trimmed = items[:top_k]
    summary_bits = [f"- [{it.source.value}] {it.title}" for it in trimmed[:8]]
    return ContextPacket(
        query=user_query,
        items=trimmed,
        summary="Retrieved context:\n" + "\n".join(summary_bits),
    )
