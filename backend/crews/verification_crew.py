
"""
crews/verification_crew.py

Public entry point for JobShield AI verification.

The coordinator collects evidence and calculates the authoritative score.
The hierarchical crew interprets that evidence and creates an investigation
report. The completed result is persisted exactly once.
"""

import json
import logging

from backend.agents.coordinator import (
    build_verification_result,
    collect_verification_evidence,
    persist_verification_result,
)
from backend.crews.hierarchical_crew import create_hierarchical_crew

logger = logging.getLogger(__name__)


def verify_company(
    company_name: str,
    cin: str = "",
    website: str = "",
    offer_text: str = "",
) -> dict:
    """Run evidence collection, manager-led analysis, scoring, and persistence."""

    # 1. Collect the initial evidence once.
    try:
        evidence = collect_verification_evidence(
            company_name=company_name,
            cin=cin,
            website=website,
            offer_text=offer_text,
        )
    except (ValueError, TypeError) as exc:
        return {
            "status": "invalid_input",
            "error": str(exc),
        }

    # 2. Calculate the authoritative deterministic score.
    result = build_verification_result(evidence)

    # 3. Let the manager interpret the evidence and identify meaningful gaps.
    # Crew failure must not discard the deterministic verification result.
    investigation_input = {
        "submitted_information": {
            "company_name": evidence["company_name"],
            "cin": evidence["cin"] or None,
            "website": evidence["website"] or None,
            "offer_text_provided": bool(evidence["offer_text"]),
        },
        "initial_evidence": evidence["checks"],
        "authoritative_scoring": result["scoring"],
        "limitations": result["limitations"],
    }

    try:
        crew = create_hierarchical_crew()
        report = crew.kickoff(
            inputs={
                "investigation_input": json.dumps(
                    investigation_input,
                    ensure_ascii=False,
                    default=str,
                )
            }
        )
        result["investigation"] = {
            "status": "completed",
            "report": str(report),
        }
    except Exception as exc:
        # Keep the deterministic result usable even if the LLM provider,
        # manager, or a delegated specialist is temporarily unavailable.
        logger.exception("Manager-led investigation failed")
        result["investigation"] = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "report": (
                "The deterministic checks completed, but the "
                "manager-led investigation report could not be generated."
            ),
        }

    # 4. Save the final result, including the manager report, once.
    return persist_verification_result(result)
