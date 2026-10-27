
"""
tools/database/verification_history_tool.py

Save and retrieve JobShield AI verification history.
Reuses the shared MongoDB connection.
"""

from datetime import datetime, timezone

from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from backend.database.connection import get_db
from backend.database.collections import VERIFICATION_HISTORY


def _normalize_company_name(name: str) -> str:
    """Create a consistent key for company-history searches."""
    return " ".join(name.strip().lower().split())


def _serialize_document(document: dict) -> dict:
    """Convert MongoDB-specific values into JSON-friendly values."""
    document["_id"] = str(document["_id"])

    for field in ("created_at",):
        value = document.get(field)
        if isinstance(value, datetime):
            document[field] = value.isoformat()

    return document


def save_verification(
    company_name: str,
    verification_result: dict,
) -> dict:
    """
    Save one completed verification result.

    Database failures are returned as errors, not fraud findings.
    """
    if not isinstance(company_name, str) or not company_name.strip():
        return {
            "status": "invalid_input",
            "error": "A non-empty company name is required",
        }

    if not isinstance(verification_result, dict):
        return {
            "status": "invalid_input",
            "error": "verification_result must be a dictionary",
        }

    company_name = " ".join(company_name.strip().split())

    document = {
        "company_name": company_name,
        "normalized_company_name": _normalize_company_name(company_name),
        "verification_result": verification_result,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        collection = get_db()[VERIFICATION_HISTORY]
        inserted = collection.insert_one(document)

        return {
            "status": "saved",
            "verification_id": str(inserted.inserted_id),
            "company_name": company_name,
            "error": None,
        }

    except (PyMongoError, RuntimeError) as exc:
        return {
            "status": "error",
            "verification_id": None,
            "company_name": company_name,
            "error": f"{type(exc).__name__}: {exc}",
        }


def get_verification_history(
    company_name: str,
    limit: int = 10,
) -> dict:
    """
    Retrieve the most recent verification records for a company.

    Results are ordered newest first.
    """
    if not isinstance(company_name, str) or not company_name.strip():
        return {
            "status": "invalid_input",
            "company_name": None,
            "history": [],
            "error": "A non-empty company name is required",
        }

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        return {
            "status": "invalid_input",
            "company_name": company_name.strip(),
            "history": [],
            "error": "limit must be a positive integer",
        }

    company_name = " ".join(company_name.strip().split())

    try:
        collection = get_db()[VERIFICATION_HISTORY]

        cursor = (
            collection.find({
                "normalized_company_name": _normalize_company_name(
                    company_name
                )
            })
            .sort("created_at", DESCENDING)
            .limit(min(limit, 100))
        )

        history = [_serialize_document(doc) for doc in cursor]

        return {
            "status": "found" if history else "not_found",
            "company_name": company_name,
            "history": history,
            "count": len(history),
            "error": None,
        }

    except (PyMongoError, RuntimeError) as exc:
        return {
            "status": "error",
            "company_name": company_name,
            "history": [],
            "count": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
