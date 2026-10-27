
"""
tools/scoring/red_flag_scorer_tool.py

Deterministic, explainable risk scoring for JobShield AI.
No LLM or external API required.

Important:
- A risk score is not proof of fraud.
- Missing evidence is not automatically negative evidence.
- Tool/API failures must never increase the score.
"""

SEVERITY_POINTS = {
    "high": 25,
    "medium": 12,
    "low": 5,
}

MAX_RISK_SCORE = 100


def _validate_finding(finding: dict) -> bool:
    """Check whether a finding has the minimum expected structure."""
    return (
        isinstance(finding, dict)
        and finding.get("severity") in SEVERITY_POINTS
        and isinstance(finding.get("rule_id"), str)
        and bool(finding["rule_id"].strip())
    )


def score_risk(findings: list[dict]) -> dict:
    """
    Calculate a risk score from structured findings.

    Each distinct rule contributes:
      high   = 25 points
      medium = 12 points
      low    = 5 points

    The score is capped at 100.

    Duplicate rule IDs are counted only once, preventing repeated
    occurrences of the same rule from inflating the score.

    Args:
        findings: A list of findings from tools such as scan_offer().

    Returns:
        A dictionary containing score, risk level, explanations,
        and input-validation information.
    """
    if not isinstance(findings, list):
        return {
            "status": "invalid_input",
            "risk_score": None,
            "risk_level": None,
            "findings_considered": [],
            "ignored_findings": 0,
            "error": "findings must be a list",
        }

    valid_findings = []
    seen_rule_ids = set()
    ignored_findings = 0

    for finding in findings:
        if not _validate_finding(finding):
            ignored_findings += 1
            continue

        rule_id = finding["rule_id"].strip()

        if rule_id in seen_rule_ids:
            continue

        seen_rule_ids.add(rule_id)
        valid_findings.append(finding)

    raw_score = sum(
        SEVERITY_POINTS[finding["severity"]]
        for finding in valid_findings
    )

    risk_score = min(raw_score, MAX_RISK_SCORE)

    if risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 30:
        risk_level = "medium"
    elif risk_score > 0:
        risk_level = "low"
    else:
        risk_level = "no_flags_detected"

    explanations = [
        {
            "rule_id": finding["rule_id"],
            "severity": finding["severity"],
            "points": SEVERITY_POINTS[finding["severity"]],
            "evidence": finding.get("evidence", ""),
            "recommendation": finding.get("recommendation", ""),
        }
        for finding in valid_findings
    ]

    return {
        "status": "scored",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "findings_considered": explanations,
        "ignored_findings": ignored_findings,
        "error": None,
        "disclaimer": (
            "This score represents detected risk indicators, "
            "not a definitive determination of fraud. "
            "No detected flags does not guarantee legitimacy."
        ),
    }
