
"""
tools/communication/offer_scan_tool.py

Rule-based scanner for suspicious job postings and offer letters.
Standalone Python implementation; CrewAI integration comes later.

Important:
- Findings are risk indicators, not proof of fraud.
- No LLM or external API is required.
- This tool does not calculate the final fraud score.
"""

import re


# Each rule contains:
# (rule_id, category, pattern, severity, recommendation)

_RULES = [
    (
        "UPFRONT_PAYMENT",
        "payment_request",
        re.compile(
            r"\b(?:pay|paying|payment of|deposit|transfer|"
            r"remit|submit)\b.{0,65}?"
            r"(?:registration fee|application fee|processing fee|"
            r"security deposit|training fee|interview fee|"
            r"placement fee|verification fee|joining fee|"
            r"recruitment fee|refundable fee)\b"
            r"|"
            r"\b(?:registration fee|application fee|processing fee|"
            r"security deposit|training fee|interview fee|"
            r"placement fee|verification fee|joining fee|"
            r"recruitment fee|refundable fee)\b.{0,65}?"
            r"\b(?:pay|payment|deposit|transfer|required|mandatory)\b",
            re.IGNORECASE,
        ),
        "high",
        "Verify the fee through the employer's official hiring channels. "
        "Requests for payment to obtain a job are a significant warning sign.",
    ),
    (
        "GUARANTEED_JOB",
        "unrealistic_promise",
        re.compile(
            r"\b(?:100\s*%\s*)?(?:guaranteed|assured)\s+"
            r"(?:job|placement|employment|selection|offer)\b"
            r"|\b(?:job|placement|employment)\s+"
            r"(?:is\s+)?guaranteed\b",
            re.IGNORECASE,
        ),
        "medium",
        "Verify the hiring process and employment claims independently.",
    ),
    (
        "UNREALISTIC_SALARY",
        "salary_claim",
        re.compile(
            r"\b(?:earn|salary|income|make)\b.{0,45}?"
            r"(?:₹|rs\.?\s*|inr\s*)?\d[\d,]*(?:\.\d+)?\s*"
            r"(?:lpa|lakhs?\s+per\s+annum|"
            r"(?:per|a)\s+(?:day|week|month|hour))\b"
            r".{0,45}?\b(?:no experience|without experience|"
            r"no skills required|easy money|guaranteed income)\b"
            r"|"
            r"\b(?:no experience|without experience|"
            r"no skills required|easy money|guaranteed income)\b"
            r".{0,45}?\b(?:earn|salary|income|make)\b"
            r".{0,45}?(?:₹|rs\.?\s*|inr\s*)?\d[\d,]*",
            re.IGNORECASE,
        ),
        "medium",
        "Check whether the compensation is realistic for the role, "
        "experience level and stated working hours.",
    ),
    (
        "SENSITIVE_CREDENTIAL_REQUEST",
        "sensitive_information",
        re.compile(
            r"\b(?:share|send|provide|reveal|submit|tell us|"
            r"enter|forward)\b.{0,55}?"
            r"\b(?:password|bank pin|upi pin|atm pin|"
            r"card cvv|security code|net banking credentials)\b"
            r"|"
            r"\b(?:password|bank pin|upi pin|atm pin|"
            r"card cvv|net banking credentials)\b.{0,55}?"
            r"\b(?:share|send|provide|reveal|submit|required)\b",
            re.IGNORECASE,
        ),
        "high",
        "Never share passwords, banking PINs or card security codes "
        "with a recruiter. Verify any request through official channels.",
    ),
    (
        "URGENT_PAYMENT_PRESSURE",
        "pressure_tactic",
        re.compile(
            r"\b(?:pay|payment|transfer|deposit)\b.{0,50}?"
            r"\b(?:immediately|within \d+\s*(?:minutes?|hours?)|"
            r"right now|today only)\b"
            r"|"
            r"\b(?:immediately|within \d+\s*(?:minutes?|hours?)|"
            r"right now|today only)\b.{0,50}?"
            r"\b(?:pay|payment|transfer|deposit)\b",
            re.IGNORECASE,
        ),
        "medium",
        "Do not rush into payment. Independently verify the recruiter "
        "and the reason for the deadline.",
    ),
    (
        "UNOFFICIAL_CONTACT_CHANNEL",
        "communication_channel",
        re.compile(
            r"\b(?:contact|message|send your documents|"
            r"send documents|continue the interview)\b.{0,60}?"
            r"\b(?:personal whatsapp|telegram only|"
            r"personal email|gmail\.com|yahoo\.com)\b",
            re.IGNORECASE,
        ),
        "low",
        "Verify that the contact channel belongs to the employer. "
        "Personal email or messaging accounts alone do not prove fraud.",
    ),
]


def _get_context(text: str, start: int, end: int, window: int = 100) -> str:
    """Return a readable excerpt around a matched phrase."""
    left = max(0, start - window)
    right = min(len(text), end + window)

    excerpt = text[left:right].strip()
    if left > 0:
        excerpt = "..." + excerpt
    if right < len(text):
        excerpt += "..."

    return excerpt


def _is_negated(text: str, start: int, end: int) -> bool:
    """
    Avoid obvious false positives when a document warns against a scam.

    This is a conservative text heuristic, not full language understanding.
    """
    before = text[max(0, start - 45):start].lower()
    after = text[end:min(len(text), end + 35)].lower()

    negative_prefixes = (
        "do not ",
        "don't ",
        "never ",
        "avoid ",
        "no ",
        "without ",
        "not required to ",
        "not required ",
        "should not ",
    )

    if any(before.endswith(prefix) for prefix in negative_prefixes):
        return True

    # Example: "No registration fee is required."
    if re.match(
        r"\s+(?:is\s+)?(?:not\s+required|is\s+not\s+required|"
        r"is\s+unnecessary|is\s+waived)\b",
        after,
    ):
        return True

    return False


def scan_offer(text: str) -> dict:
    """
    Scan a job description, recruitment message or offer letter.

    Returns:
        {
            "status": "scanned" | "invalid_input",
            "findings": [
                {
                    "rule_id": str,
                    "category": str,
                    "severity": str,
                    "evidence": str,
                    "recommendation": str
                }
            ],
            "findings_count": int,
            "severity_counts": {"high": int, "medium": int, "low": int}
        }

    A successful scan with no findings does not establish legitimacy.
    """
    if not isinstance(text, str) or not text.strip():
        return {
            "status": "invalid_input",
            "findings": [],
            "findings_count": 0,
            "severity_counts": {"high": 0, "medium": 0, "low": 0},
            "error": "Non-empty offer text is required",
        }

    findings = []
    seen = set()

    for rule_id, category, pattern, severity, recommendation in _RULES:
        for match in pattern.finditer(text):
            if _is_negated(text, match.start(), match.end()):
                continue

            evidence = _get_context(text, match.start(), match.end())
            deduplication_key = (rule_id, evidence.lower())

            if deduplication_key in seen:
                continue

            seen.add(deduplication_key)

            findings.append({
                "rule_id": rule_id,
                "category": category,
                "severity": severity,
                "evidence": evidence,
                "recommendation": recommendation,
            })

    severity_counts = {
        severity: sum(
            1 for finding in findings
            if finding["severity"] == severity
        )
        for severity in ("high", "medium", "low")
    }

    return {
        "status": "scanned",
        "findings": findings,
        "findings_count": len(findings),
        "severity_counts": severity_counts,
        "error": None,
    }
