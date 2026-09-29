"""
tools/registry/mca_lookup_tool.py

Placeholder — MCA (Ministry of Corporate Affairs) company registry lookup
via data.gov.in Open Government Data API. To be implemented.
"""
"""
MCA registry lookup via data.gov.in.

Plain functions first (test standalone), CrewAI @tool wrapper added at the bottom
once the integration is proven.

Key design rule: "not found" and "lookup failed" are DIFFERENT outcomes.
The scorer must never treat an API error as evidence of fraud.
"""
import re
import requests

from config import settings

# --- CIN parsing (offline sanity check, no API needed) -----------------------
_CIN_RE = re.compile(r"^([LU])(\d{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$")


def parse_cin(cin: str) -> dict | None:
    """Split a CIN into parts. Returns None if the format is invalid."""
    m = _CIN_RE.match((cin or "").strip().upper())
    if not m:
        return None
    listing, industry, state, year, ownership, serial = m.groups()
    return {
        "listing_status": "Listed" if listing == "L" else "Unlisted",
        "nic_code": industry,
        "state_code": state,
        "incorporation_year": int(year),
        "ownership_code": ownership,  # e.g. PTC = private, PLC = public
        "serial": serial,
    }


# --- Name normalisation -------------------------------------------------------
_SUFFIXES = [
    (r"\bPVT\.?\s*LTD\.?\b", "PRIVATE LIMITED"),
    (r"\bPRIVATE\s+LTD\.?\b", "PRIVATE LIMITED"),
    (r"\bLTD\.?\b", "LIMITED"),
]


def normalize_name(name: str) -> str:
    n = (name or "").upper().strip()
    n = n.replace("&", " AND ")
    for pat, repl in _SUFFIXES:
        n = re.sub(pat, repl, n)
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _strip_suffix(name: str) -> str:
    return re.sub(r"\s+(PRIVATE LIMITED|LIMITED|LLP)$", "", name).strip()


def candidate_names(name: str) -> list[str]:
    """Exact-match filters are brittle, so try the likely registered forms."""
    norm = normalize_name(name)
    base = _strip_suffix(norm)
    seen, out = set(), []
    for c in (norm, f"{base} PRIVATE LIMITED", f"{base} LIMITED", base):
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


# --- Record mapping -----------------------------------------------------------
# Field names differ between datasets; match case-insensitively on aliases.
_ALIASES = {
    "cin": ["cin", "corporate_identification_number", "corporate_identity_number"],
    "name": ["company_name", "companyname", "name"],
    "status": ["company_status", "companystatus", "status"],
    "incorporation_date": [
        "date_of_registration", "dateofregistration",
        "company_registration_date", "registration_date", "date_of_incorporation",
    ],
    "roc": ["company_roc_code", "roc_code", "roc", "rocname"],
    "class": ["company_class", "companyclass"],
    "category": ["company_category", "companycategory"],
    "authorized_capital": ["authorized_cap", "authorized_capital", "authorised_capital"],
    "paidup_capital": ["paidup_capital", "paid_up_capital"],
    "listing_status": ["listing_status", "whether_listed_or_not"],
}


def _pick(record: dict, key: str):
    lowered = {str(k).lower(): v for k, v in record.items()}
    for alias in _ALIASES[key]:
        if alias in lowered and lowered[alias] not in (None, ""):
            return lowered[alias]
    return None


def map_record(record: dict) -> dict:
    out = {k: _pick(record, k) for k in _ALIASES}
    out["raw"] = record  # keep raw until the schema is confirmed
    return out


# --- HTTP ---------------------------------------------------------------------
class MCAApiError(Exception):
    pass


def _query(resource_id: str, filters: dict, limit: int = 10) -> list[dict]:
    if not settings.DATA_GOV_API_KEY:
        raise MCAApiError("DATA_GOV_API_KEY is not set")
    params = {
        "api-key": settings.DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit,
    }
    for field, value in filters.items():
        params[f"filters[{field}]"] = value
    url = f"{settings.DATA_GOV_BASE_URL}/{resource_id}"
    try:
        resp = requests.get(url, params=params, timeout=settings.MCA_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json().get("records", []) or []
    except (requests.RequestException, ValueError) as e:
        raise MCAApiError(f"{type(e).__name__}: {e}") from e


def _search(filters: dict) -> tuple[list[dict], list[str]]:
    """Query every configured resource. Returns (records, errors)."""
    if not settings.MCA_RESOURCE_IDS:
        raise MCAApiError("MCA_RESOURCE_IDS is not set")
    records, errors = [], []
    for rid in settings.MCA_RESOURCE_IDS:
        try:
            records.extend(_query(rid, filters))
        except MCAApiError as e:
            errors.append(f"{rid}: {e}")
    return records, errors


# --- Public API ---------------------------------------------------------------
def lookup_company(name: str) -> dict:
    """
    Returns:
      {"status": "found" | "not_found" | "error",
       "matches": [mapped records], "tried": [names], "errors": [..]}
    """
    tried, matches, errors = [], [], []
    for cand in candidate_names(name):
        tried.append(cand)
        try:
            recs, errs = _search({settings.MCA_NAME_FIELD: cand})
        except MCAApiError as e:
            return {"status": "error", "matches": [], "tried": tried, "errors": [str(e)]}
        errors.extend(errs)
        if recs:
            matches = [map_record(r) for r in recs]
            break
    if matches:
        status = "found"
    elif errors and len(errors) >= len(settings.MCA_RESOURCE_IDS) * len(tried):
        status = "error"  # every call failed -> we know nothing
    else:
        status = "not_found"
    return {"status": status, "matches": matches, "tried": tried, "errors": errors}


def lookup_cin(cin: str) -> dict:
    """Verify a CIN quoted in an offer letter. Includes the offline format check."""
    cin = (cin or "").strip().upper()
    parsed = parse_cin(cin)
    if parsed is None:
        return {"status": "invalid_format", "cin": cin, "matches": [], "errors": []}
    try:
        recs, errs = _search({settings.MCA_CIN_FIELD: cin})
    except MCAApiError as e:
        return {"status": "error", "cin": cin, "parsed": parsed, "matches": [], "errors": [str(e)]}
    status = "found" if recs else ("error" if errs else "not_found")
    return {"status": status, "cin": cin, "parsed": parsed,
            "matches": [map_record(r) for r in recs], "errors": errs}