"""LifeGraph - in-memory graph over entities and relations."""

from typing import Iterator

import networkx as nx

from .schema import Entity, Relation, RelationType


class LifeGraph:
    """Directed graph over LifeGraph entities and relations.

    Supports traversal, neighborhood queries, and structural retrieval.
    """

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()

    def add_entity(self, entity: Entity) -> None:
        """Add or update an entity node."""
        self._g.add_node(
            entity.id,
            type=entity.type,
            title=entity.title,
            description=entity.description,
            data=entity,
        )

    def add_relation(self, relation: Relation) -> None:
        """Add an edge between entities."""
        self._g.add_edge(
            relation.source_id,
            relation.target_id,
            relation_type=relation.relation_type,
            data=relation,
        )

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        if not self._g.has_node(entity_id):
            return None
        return self._g.nodes[entity_id].get("data")

    def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[RelationType] | None = None,
        direction: str = "both",
    ) -> list[Entity]:
        """Get neighboring entities, optionally filtered by relation type."""
        if not self._g.has_node(entity_id):
            return []

        entities: list[Entity] = []
        if direction in ("out", "both"):
            for _, target_id, data in self._g.out_edges(entity_id, data=True):
                rt = data.get("relation_type")
                if relation_types is None or rt in relation_types:
                    e = self.get_entity(target_id)
                    if e:
                        entities.append(e)
        if direction in ("in", "both"):
            for source_id, _, data in self._g.in_edges(entity_id, data=True):
                rt = data.get("relation_type")
                if relation_types is None or rt in relation_types:
                    e = self.get_entity(source_id)
                    if e:
                        entities.append(e)
        return entities

    def get_blocked_by(self, entity_id: str) -> list[Entity]:
        """Get entities that block this one."""
        return self.get_neighbors(
            entity_id,
            relation_types=[RelationType.BLOCKS],
            direction="in",
        )

    def get_dependencies(self, entity_id: str) -> list[Entity]:
        """Get entities this one depends on."""
        return self.get_neighbors(
            entity_id,
            relation_types=[RelationType.DEPENDS_ON],
            direction="out",
        )

    def all_entities(self) -> Iterator[Entity]:
        """Iterate all entities."""
        for _, data in self._g.nodes(data=True):
            e = data.get("data")
            if isinstance(e, Entity):
                yield e

    def all_relations(self) -> Iterator[tuple[str, str, Relation]]:
        """Iterate all relations as (source_id, target_id, relation)."""
        for u, v, data in self._g.edges(data=True):
            r = data.get("data")
            if isinstance(r, Relation):
                yield u, v, r

    def clear(self) -> None:
        """Clear the graph."""
        self._g.clear()
