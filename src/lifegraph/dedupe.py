"""Heuristics to identify and merge duplicate entities across connectors."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .schema import Entity, EntityType

if TYPE_CHECKING:
    from .graph import LifeGraph


def _normalize_title(title: str) -> str:
    # Lowercase, remove special chars, remove common fillers
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\b(the|a|an|and|or|re|fwd)\b", "", t)
    return " ".join(t.split())


def find_duplicates(entity: Entity, graph: LifeGraph) -> str | None:
    """Return the ID of an existing entity that matches this one, if any."""
    norm_title = _normalize_title(entity.title)
    if not norm_title:
        return None

    for existing in graph.all_entities():
        # Only compare same types (or related types like Task/Goal)
        if existing.type != entity.type:
            continue
            
        if existing.id == entity.id:
            continue

        ext_title = _normalize_title(existing.title)
        
        # Exact title match (after normalization)
        if norm_title == ext_title:
            return existing.id
            
        # Partial match if titles are long enough
        if len(norm_title) > 10 and len(ext_title) > 10:
            if norm_title in ext_title or ext_title in norm_title:
                return existing.id

    return None


def merge_entities(primary_id: str, secondary_id: str, graph: LifeGraph) -> None:
    """Merge secondary entity into primary, updating relations."""
    # This would involve updating the 'relations' table in storage
    # For now, we'll keep it as a conceptual placeholder or simple graph update
    pass
