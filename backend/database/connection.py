"""
database/connection.py

Single shared MongoDB client for the whole app. Tools import get_db()
instead of each opening their own connection.
"""
from pymongo import MongoClient
from pymongo.database import Database

from backend.config import settings

_client: MongoClient | None = None
_db: Database | None = None


def get_db() -> Database:
    global _client, _db
    if _db is None:
        if not settings.MONGO_URI:
            raise RuntimeError(
                "MONGO_URI not set. Copy .env.example to .env and fill it in."
            )
        _client = MongoClient(settings.MONGO_URI)
        _db = _client[settings.MONGO_DB_NAME]
    return _db


def ping() -> bool:
    """Quick connectivity check, used by the Phase 1 checkpoint script."""
    try:
        get_db().command("ping")
        return True
    except Exception:
        return False
