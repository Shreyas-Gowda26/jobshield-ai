
"""
tools/web_presence/whois_tool.py

Domain registration lookup for JobShield AI.

Standalone Python functions first; CrewAI integration comes later.
A missing creation date is not proof that a domain is suspicious.
"""

import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse
import whois

def normalize_domain(value: str) -> str:
    """Convert a URL or domain input into a normalized hostname."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A website URL or domain is required")

    value = value.strip()

    # Make bare domains parseable as URLs.
    if "://" not in value:
        value = f"//{value}"

    parsed = urlparse(value, scheme="https")
    hostname = parsed.hostname

    if not hostname:
        raise ValueError("Could not extract a domain from the input")

    hostname = hostname.rstrip(".").lower()

    # Reject IP addresses and malformed hostnames for this tool.
    if len(hostname) > 253 or "." not in hostname:
        raise ValueError("A valid public domain name is required")

    labels = hostname.split(".")
    label_pattern = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

    if not all(label_pattern.fullmatch(label) for label in labels):
        raise ValueError("The domain name has an invalid format")

    if any(not label for label in labels):
        raise ValueError("The domain name has an invalid format")

    return hostname


def _first_date(value):
    """WHOIS date fields may contain one date or a list of dates."""
    if isinstance(value, (list, tuple)):
        value = next((item for item in value if item is not None), None)

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    return None


def lookup_domain(domain_input: str) -> dict:
    """
    Return structured WHOIS results.

    Status values:
      found          Registration data was returned.
      not_available  Lookup succeeded but useful registration data was absent.
      error          The lookup failed.
      invalid_input  The supplied domain was invalid.
    """
    try:
        domain = normalize_domain(domain_input)
    except (TypeError, ValueError) as exc:
        return {
            "status": "invalid_input",
            "domain": None,
            "error": str(exc),
        }

    try:
        import whois

        record = whois.whois(domain)

        created = _first_date(record.creation_date)
        expires = _first_date(record.expiration_date)
        updated = _first_date(record.updated_date)

        now = datetime.now(timezone.utc)

        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if updated and updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)

        age_days = (
            max(0, (now - created).days)
            if created and created <= now
            else None
        )

        def iso(value):
            return value.isoformat() if value else None

        registrar = getattr(record, "registrar", None)
        nameservers = getattr(record, "name_servers", None) or []

        if isinstance(nameservers, str):
            nameservers = [nameservers]

        nameservers = sorted({
            str(server).lower()
            for server in nameservers
            if server
        })

        has_data = any([
            created,
            expires,
            updated,
            registrar,
            nameservers,
        ])

        return {
            "status": "found" if has_data else "not_available",
            "domain": domain,
            "registrar": registrar,
            "creation_date": iso(created),
            "expiration_date": iso(expires),
            "updated_date": iso(updated),
            "domain_age_days": age_days,
            "name_servers": nameservers,
            "error": None,
        }

    except Exception as exc:
        # Preserve the distinction between unavailable data and a failed lookup.
        return {
            "status": "error",
            "domain": domain,
            "error": f"{type(exc).__name__}: {exc}",
        }
