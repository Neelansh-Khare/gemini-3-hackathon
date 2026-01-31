"""Life OS entry point. Run: uvicorn src.main:app --reload"""

from src.orchestration.api import app

__all__ = ["app"]
