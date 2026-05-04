"""Fetch from connectors, normalize, rank into a compact ContextPacket."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import math
from google import genai

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


async def _get_embeddings(texts: list[str], client: genai.Client) -> list[list[float]]:
    """Fetch embeddings in batch using Gemini."""
    try:
        response = await client.aio.models.embed_content(
            model="text-embedding-004",
            content=texts,
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )
        return [e.values for e in response.embeddings]
    except Exception:
        return []


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


async def assemble_context(
    user_query: str,
    gmail: GmailConnector,
    calendar: CalendarConnector,
    notion: NotionConnector,
    obsidian: ObsidianConnector,
    top_k: int = 24,
    gemini_api_key: str | None = None,
) -> ContextPacket:
    """Build ranked context from all four mock connectors with dynamic weighting and optional vector search."""
    items: list[ContextItem] = []
    
    # Detect intent to adjust weights
    q_lower = user_query.lower()
    time_sensitive = any(w in q_lower for w in ["next", "week", "today", "tomorrow", "deadline", "soon", "meeting", "schedule"])
    
    # Weights: Relevance (Keyword/Vector), Importance, Recency
    if time_sensitive:
        w_rel, w_imp, w_rec = 0.35, 0.20, 0.45
    else:
        w_rel, w_imp, w_rec = 0.50, 0.30, 0.20

    # 1. Gather all raw items
    raw_data: list[tuple[dict[str, Any], ConnectorName, str]] = []
    
    for t in gmail.list_threads():
        raw_data.append((t, ConnectorName.GMAIL, "thread"))
    for e in calendar.list_events():
        raw_data.append((e, ConnectorName.CALENDAR, "event"))
    for n in notion.list_items():
        raw_data.append((n, ConnectorName.NOTION, n.get("type", "task")))
    for note in obsidian.list_notes():
        raw_data.append((note, ConnectorName.OBSIDIAN, "note"))

    # 2. Compute semantic scores if API key is present
    semantic_scores: dict[str, float] = {}
    if gemini_api_key:
        client = genai.Client(api_key=gemini_api_key)
        # Prepare text for embedding
        texts_to_embed = []
        for rd, conn, kind in raw_data:
            if conn == ConnectorName.GMAIL:
                text = f"{rd.get('subject','')} {rd.get('snippet','')}"
            elif conn == ConnectorName.CALENDAR:
                text = f"{rd.get('title','')} {rd.get('location','')}"
            elif conn == ConnectorName.NOTION:
                text = f"{rd.get('title','')} {rd.get('status','')}"
            else: # Obsidian
                text = f"{rd.get('title','')} {rd.get('body','')}"
            texts_to_embed.append(text[:2000]) # Truncate for safety

        # Batch embed query and docs
        all_embeddings = await _get_embeddings([user_query] + texts_to_embed, client)
        if all_embeddings:
            query_emb = all_embeddings[0]
            doc_embs = all_embeddings[1:]
            for i, emb in enumerate(doc_embs):
                sim = _cosine_similarity(query_emb, emb)
                # Map similarity (-1 to 1) to 0-1 range
                score = (sim + 1) / 2
                # Unique key: connector + id/path
                rd, conn, _ = raw_data[i]
                item_id = rd.get("id") or rd.get("path")
                semantic_scores[f"{conn.value}:{item_id}"] = score

    # 3. Build ContextItems with combined ranking
    for rd, conn, kind in raw_data:
        item_id = rd.get("id") or rd.get("path")
        lookup_key = f"{conn.value}:{item_id}"
        
        if conn == ConnectorName.GMAIL:
            body = f"{rd.get('subject','')} {rd.get('snippet','')} {rd.get('from','')}"
            kw_score = _keyword_overlap(user_query, body)
            sem_score = semantic_scores.get(lookup_key, kw_score)
            rel_score = 0.7 * sem_score + 0.3 * kw_score
            
            imp = 0.9 if rd.get("unread") else 0.4
            if "IMPORTANT" in rd.get("labels", []):
                imp = min(1.0, imp + 0.05)
            od = rd.get("internal_date")
            occ = od if isinstance(od, datetime) else None
            reason = f"Semantic match: {sem_score:.0%}" if lookup_key in semantic_scores else f"Keyword match: {kw_score:.0%}"
            if rd.get("unread"):
                reason += " · Unread priority"
            
            items.append(
                ContextItem(
                    id=f"gmail:{rd['id']}",
                    source=ConnectorName.GMAIL,
                    kind="thread",
                    title=rd.get("subject", ""),
                    body=rd.get("snippet", ""),
                    occurred_at=occ,
                    relevance=min(1.0, rel_score),
                    importance=imp,
                    reasoning=reason,
                    metadata={"from": rd.get("from"), "unread": rd.get("unread")},
                )
            )
        elif conn == ConnectorName.CALENDAR:
            body = f"{rd.get('title','')} {rd.get('location','')}"
            st = rd.get("start")
            occ = st if isinstance(st, datetime) else None
            kw_score = _keyword_overlap(user_query, body)
            sem_score = semantic_scores.get(lookup_key, kw_score)
            rec_score = _recency_score(occ)
            rel_score = 0.4 * sem_score + 0.3 * kw_score + 0.3 * rec_score
            
            reason = f"Semantic match: {sem_score:.0%}" if lookup_key in semantic_scores else f"Keyword match: {kw_score:.0%}"
            if rec_score > 0.8:
                reason += " · Recent event"
                
            items.append(
                ContextItem(
                    id=f"cal:{rd['id']}",
                    source=ConnectorName.CALENDAR,
                    kind="event",
                    title=rd.get("title", ""),
                    body=str(rd.get("location", "")),
                    occurred_at=occ,
                    relevance=rel_score,
                    importance=0.7,
                    reasoning=reason,
                    metadata={"start": rd.get("start"), "end": rd.get("end")},
                )
            )
        elif conn == ConnectorName.NOTION:
            body = f"{rd.get('title','')} {rd.get('status','')} {rd.get('due','')}"
            kw_score = _keyword_overlap(user_query, body)
            sem_score = semantic_scores.get(lookup_key, kw_score)
            type_boost = 0.85 if rd.get("type") == "goal" else 0.65
            rel_score = 0.6 * sem_score + 0.2 * kw_score + 0.2 * type_boost
            
            reason = f"Semantic match: {sem_score:.0%}" if lookup_key in semantic_scores else f"Keyword match: {kw_score:.0%}"
            if rd.get("type") == "goal":
                reason += " · High-level goal boost"

            items.append(
                ContextItem(
                    id=f"notion:{rd['id']}",
                    source=ConnectorName.NOTION,
                    kind=rd.get("type", "task"),
                    title=rd.get("title", ""),
                    body=body,
                    occurred_at=None,
                    relevance=min(1.0, rel_score),
                    importance=0.8 if rd.get("type") == "goal" else 0.6,
                    reasoning=reason,
                    metadata={"status": rd.get("status"), "due": rd.get("due")},
                )
            )
        elif conn == ConnectorName.OBSIDIAN:
            body = f"{rd.get('title','')} {rd.get('body','')}"
            kw_score = _keyword_overlap(user_query, body)
            sem_score = semantic_scores.get(lookup_key, kw_score)
            rel_score = 0.8 * sem_score + 0.2 * kw_score
            
            items.append(
                ContextItem(
                    id=f"obs:{rd['path']}",
                    source=ConnectorName.OBSIDIAN,
                    kind="note",
                    title=rd.get("title", rd.get("path", "")),
                    body=(rd.get("body") or "")[:1500],
                    occurred_at=None,
                    relevance=min(1.0, rel_score + 0.1),
                    importance=0.55,
                    reasoning=f"Semantic match: {sem_score:.0%}" if lookup_key in semantic_scores else f"Keyword match: {kw_score:.0%}",
                    metadata={"path": rd.get("path")},
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
