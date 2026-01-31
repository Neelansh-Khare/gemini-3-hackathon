"""Hybrid retrieval: vector + graph + recency/importance scoring."""

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..lifegraph.schema import Entity
from ..lifegraph.graph import LifeGraph


class HybridRetriever:
    """Combines vector search (content) with graph traversal (structure)."""

    def __init__(self, graph: LifeGraph, vector_store_path: Path | str) -> None:
        self._graph = graph
        self._path = Path(vector_store_path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self._path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="lifegraph",
            metadata={"description": "LifeGraph entities for semantic search"},
        )

    def index_entity(self, entity: Entity) -> None:
        """Add or update entity in vector store."""
        text = f"{entity.title} {entity.description or ''}".strip()
        metadata = {
            "id": entity.id,
            "type": entity.type,
            "source_system": entity.source_system or "",
        }
        self._collection.upsert(
            ids=[entity.id],
            documents=[text],
            metadatas=[metadata],
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        entity_types: list[str] | None = None,
    ) -> list[tuple[Entity, float]]:
        """Vector search over entity content. Returns (entity, score) pairs."""
        where: dict[str, Any] = {}
        if entity_types:
            where["type"] = {"$in": entity_types}
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": top_k}
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)
        ids = results["ids"][0] if results["ids"] else []
        distances = results["distances"][0] if results.get("distances") else []
        out: list[tuple[Entity, float]] = []
        for eid, dist in zip(ids, distances):
            entity = self._graph.get_entity(eid)
            if entity:
                score = 1.0 / (1.0 + dist) if dist else 1.0
                out.append((entity, score))
        return out

    def get_context_for_intent(self, intent: str, top_k: int = 15) -> list[Entity]:
        """Retrieve relevant context for a user intent (used by orchestrator)."""
        results = self.search(intent, top_k=top_k)
        return [e for e, _ in results]
