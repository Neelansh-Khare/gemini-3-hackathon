"""Base connector interface for MCP tools. Write-back agents implement this."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from ..lifegraph.schema import Entity


class ConnectorCapability(StrEnum):
    READ = "read"
    WRITE = "write"
    APPEND = "append"


class BaseConnector(ABC):
    """Abstract base for system connectors (Gmail, Calendar, Notion, Obsidian)."""

    name: str = "base"
    capabilities: set[ConnectorCapability] = set()

    @abstractmethod
    async def sync_to_graph(self) -> list[Entity]:
        """Pull data from system into LifeGraph entities. Returns new/updated entities."""
        ...

    @abstractmethod
    async def apply_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        """Apply a structured diff. Returns result/confirmation.
        Append-only by default; overwrite requires explicit approval.
        """
        ...

    @abstractmethod
    async def rollback(self, diff: dict[str, Any]) -> dict[str, Any]:
        """Undo a previously applied diff. Returns result/confirmation."""
        ...

    @abstractmethod
    def can_handle(self, system: str) -> bool:
        """Whether this connector handles the given source system."""
        ...
