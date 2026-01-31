"""Application configuration loaded from environment."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Life OS settings. Loads from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Storage
    lifegraph_db_path: str = "./data/lifegraph.db"
    vector_db_path: str = "./data/vector_store"

    # OAuth (Gmail, Calendar)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # Notion
    notion_api_key: str = ""
    notion_database_id: str = ""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Safety
    require_approval_for_writes: bool = True

    @property
    def lifegraph_db(self) -> Path:
        return Path(self.lifegraph_db_path)

    @property
    def vector_store_path(self) -> Path:
        return Path(self.vector_db_path)


settings = Settings()
