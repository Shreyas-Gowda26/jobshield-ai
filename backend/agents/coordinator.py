
"""
agents/coordinator.py

Deterministic orchestration for JobShield AI.

Responsibilities:
- Collect external evidence.
- Calculate the authoritative deterministic risk score.
- Build a structured verification result.
- Persist verification history exactly once.

External lookup failures are never automatically treated as fraud findings.
"""

from backend.tools.registry.mca_lookup_tool import (
    lookup_company,
    lookup_cin,
)
from backend.tools.web_presence.search_presence_tool import (
    search_company_presence,
)
from backend.tools.web_presence.whois_tool import lookup_domain
from backend.tools.communication.offer_scan_tool import scan_offer
from backend.tools.scoring.red_flag_scorer_tool import score_risk
from backend.tools.database.verification_history_tool import (
    save_verification,
)


def _run_check(check_name: str, function, *args, **kwargs) -> dict:
    """Run one check without allowing its failure to stop other checks."""
    try:
        return function(*args, **kwargs)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "check": check_name,
        }


def _normalize_input(
    company_name: str,
    cin: str,
    website: str,
    offer_text: str,
) -> dict:
    """Validate and normalize verification inputs."""
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError("A non-empty company name is required")

    for field_name, value in (
        ("cin", cin),
        ("website", website),
        ("offer_text", offer_text),
    ):
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

    return {
        "company_name": " ".join(company_name.strip().split()),
        "cin": cin.strip(),
        "website": website.strip(),
        "offer_text": offer_text.strip(),
    }


def _summarize_company_identity(mca_result: dict) -> dict:
    """Summarize company-name lookup results without judging fraud."""
    status = mca_result.get("status")
    matches = mca_result.get("matches") or []
    errors = mca_result.get("errors") or []
    partial_failure = bool(errors) and status == "found"

    if status == "error":
        return {
            "status": "lookup_error",
            "matches_count": len(matches),
            "partial_failure": False,
            "message": (
                "Unable to verify company registration because "
                "the lookup failed."
            ),
        }

    if status == "invalid_input":
        return {
            "status": "invalid_input",
            "matches_count": 0,
            "partial_failure": False,
            "message": "A valid company name is required.",
        }

    if status == "not_found" or (status == "found" and not matches):
        return {
            "status": "not_found",
            "matches_count": 0,
            "partial_failure": bool(errors),
            "message": (
                "No matching company registration was found. "
                "Some lookup errors occurred."
                if errors
                else "No matching company registration was found."
            ),
        }

    if status == "found":
        if len(matches) == 1:
            summary_status = "single_match"
            message = "One matching company registration was found."
        else:
            summary_status = "multiple_matches"
            message = (
                "Multiple company registrations matched. "
                "Confirm which company is relevant."
            )

        if partial_failure:
            message += (
                " Some lookup sources failed, so verification "
                "may be incomplete."
            )

        return {
            "status": summary_status,
            "matches_count": len(matches),
            "partial_failure": partial_failure,
            "message": message,
        }

    return {
        "status": "unknown",
        "matches_count": len(matches),
        "partial_failure": bool(errors),
        "message": "Company registration could not be conclusively assessed.",
    }


def collect_verification_evidence(
    company_name: str,
    cin: str = "",
    website: str = "",
    offer_text: str = "",
) -> dict:
    """
    Collect evidence without calculating the final score or saving history.

    Returns normalized inputs and the raw results of applicable checks.
    Raises ValueError or TypeError for invalid inputs.
    """
    normalized = _normalize_input(company_name, cin, website, offer_text)

    company_name = normalized["company_name"]
    cin = normalized["cin"]
    website = normalized["website"]
    offer_text = normalized["offer_text"]

    checks = {
        "mca_company": _run_check(
            "mca_company",
            lookup_company,
            company_name,
        )
    }

    if cin:
        checks["mca_cin"] = _run_check(
            "mca_cin",
            lookup_cin,
            cin,
        )

    checks["web_presence"] = _run_check(
        "web_presence",
        search_company_presence,
        company_name,
        website=website or None,
    )

    # Only perform WHOIS when the user supplied a website explicitly.
    if website:
        checks["domain_registration"] = _run_check(
            "domain_registration",
            lookup_domain,
            website,
        )

    if offer_text:
        checks["offer_scan"] = _run_check(
            "offer_scan",
            scan_offer,
            offer_text,
        )

    return {
        "company_name": company_name,
        "cin": cin,
        "website": website,
        "offer_text": offer_text,
        "checks": checks,
    }


def build_verification_result(evidence: dict) -> dict:
    """
    Build the structured result and calculate the authoritative score once.

    Only findings from a successfully completed deterministic offer scan
    contribute to the score.
    """
    checks = evidence["checks"]
    scan_result = checks.get("offer_scan", {})

    offer_findings = []
    if scan_result.get("status") == "scanned":
        offer_findings = scan_result.get("findings", [])

    scoring_result = score_risk(offer_findings)

    return {
        "status": "completed",
        "company_name": evidence["company_name"],
        "company_identity": _summarize_company_identity(
            checks["mca_company"]
        ),
        "checks": checks,
        "scoring": scoring_result,
        "limitations": [
            "A missing registry match or failed lookup does not prove fraud.",
            "No detected offer-text flags does not guarantee legitimacy.",
            (
                "The numeric score reflects configured red-flag rules, "
                "not a statistically validated probability of fraud."
            ),
        ],
    }


def persist_verification_result(result: dict) -> dict:
    """Save a completed result once and attach the history-save outcome."""
    history_result = _run_check(
        "verification_history",
        save_verification,
        result["company_name"],
        result,
    )
    result["history"] = history_result
    return result


def run_verification(
    company_name: str,
    cin: str = "",
    website: str = "",
    offer_text: str = "",
) -> dict:
    """
    Backwards-compatible public coordinator entry point.

    Existing callers still receive a complete result with a history status.
    """
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

    result = build_verification_result(evidence)
    return persist_verification_result(result)
