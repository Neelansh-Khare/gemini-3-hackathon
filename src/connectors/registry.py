"""Registered connector set for orchestration and execute."""

from __future__ import annotations

from .calendar import CalendarConnector
from .gmail import GmailConnector
from .notion import NotionConnector
from .obsidian import ObsidianConnector


def mock_connectors() -> list[GmailConnector | CalendarConnector | NotionConnector | ObsidianConnector]:
    """Fresh mock connector bundle (in-memory demo state)."""
    return [
        GmailConnector(),
        CalendarConnector(),
        NotionConnector(),
        ObsidianConnector(),
    ]
