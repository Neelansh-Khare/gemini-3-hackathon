"""LifeGraph persistence - SQLite-backed storage."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

from .schema import Entity, EntityType, Relation, RelationType
from .graph import LifeGraph


class LifeGraphStorage:
    """Persists LifeGraph to SQLite. Append-only by default."""

    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source_system TEXT,
                    source_id TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    payload TEXT
                );
                CREATE TABLE IF NOT EXISTS relations (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT,
                    FOREIGN KEY (source_id) REFERENCES entities(id),
                    FOREIGN KEY (target_id) REFERENCES entities(id),
                    PRIMARY KEY (source_id, target_id, relation_type)
                );
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
                CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source_system, source_id);
                CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
                CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _entity_from_row(self, row: sqlite3.Row) -> Entity:
        data = dict(row)
        payload = json.loads(data.pop("payload", "{}"))
        entity_type = EntityType(data["type"])
        return _entity_factory(entity_type, payload)

    def load(self) -> LifeGraph:
        """Load full graph from storage."""
        g = LifeGraph()
        with self._connect() as conn:
            for row in conn.execute("SELECT * FROM entities"):
                e = self._entity_from_row(row)
                g.add_entity(e)
            for row in conn.execute("SELECT * FROM relations"):
                r = Relation(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    relation_type=RelationType(row["relation_type"]),
                    metadata=json.loads(row["metadata"] or "{}"),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                g.add_relation(r)
        return g

    def save_entity(self, entity: Entity) -> None:
        """Upsert a single entity."""
        payload = entity.model_dump()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO entities (id, type, title, description, source_system, source_id, metadata, created_at, updated_at, payload)
                VALUES (:id, :type, :title, :description, :source_system, :source_id, :metadata, :created_at, :updated_at, :payload)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    metadata=excluded.metadata,
                    updated_at=excluded.updated_at,
                    payload=excluded.payload
                """,
                {
                    "id": entity.id,
                    "type": entity.type,
                    "title": entity.title,
                    "description": entity.description or "",
                    "source_system": entity.source_system or "",
                    "source_id": entity.source_id or "",
                    "metadata": json.dumps(entity.metadata),
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat(),
                    "payload": json.dumps(payload),
                },
            )
            conn.commit()

    def save_relation(self, relation: Relation) -> None:
        """Upsert a relation."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO relations (source_id, target_id, relation_type, metadata, created_at)
                VALUES (:source_id, :target_id, :relation_type, :metadata, :created_at)
                ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET
                    metadata=excluded.metadata
                """,
                {
                    "source_id": relation.source_id,
                    "target_id": relation.target_id,
                    "relation_type": relation.relation_type,
                    "metadata": json.dumps(relation.metadata),
                    "created_at": relation.created_at.isoformat(),
                },
            )
            conn.commit()


def _entity_factory(entity_type: EntityType, payload: dict) -> Entity:
    """Reconstruct entity from stored payload."""
    from .schema import Person, Project, Goal, Task, Event, Decision, Note, Communication

    mapping = {
        EntityType.PERSON: Person,
        EntityType.PROJECT: Project,
        EntityType.GOAL: Goal,
        EntityType.TASK: Task,
        EntityType.EVENT: Event,
        EntityType.DECISION: Decision,
        EntityType.NOTE: Note,
        EntityType.COMMUNICATION: Communication,
    }
    cls = mapping.get(entity_type, Entity)
    return cls.model_validate(payload)
