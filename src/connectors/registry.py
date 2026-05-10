"""Registered connector set for orchestration and execute."""

from __future__ import annotations

from .calendar import CalendarConnector
from .gmail import GmailConnector
from .notion import NotionConnector
from .obsidian import ObsidianConnector


def mock_connectors(
    obsidian_vault_path: str | None = None,
    notion_api_key: str | None = None,
    notion_database_id: str | None = None,
    google_token_path: str = "token.json",
    google_credentials_path: str = "credentials.json",
) -> list[GmailConnector | CalendarConnector | NotionConnector | ObsidianConnector]:
    """Connector bundle (switches to real if credentials provided)."""
    return [
        GmailConnector(token_path=google_token_path, creds_path=google_credentials_path),
        CalendarConnector(token_path=google_token_path, creds_path=google_credentials_path),
        NotionConnector(api_key=notion_api_key, database_id=notion_database_id),
        ObsidianConnector(vault_path=obsidian_vault_path),
    ]
