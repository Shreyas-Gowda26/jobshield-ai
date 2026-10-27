"""
tools/registry/mca_lookup_tool.py

MCA registry lookup via data.gov.in.

Plain functions first (test standalone), CrewAI @tool wrapper added at the bottom
once the integration is proven.

Key design rule: "not found" and "lookup failed" are DIFFERENT outcomes.
The scorer must never treat an API error as evidence of fraud.
"""
import re
import requests

from backend.config import settings

# --- CIN parsing (offline sanity check, no API needed) -----------------------
_CIN_RE = re.compile(r"^([LU])(\d{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$")
_VALID_CIN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CT", "DN", "DD",
    "DL", "GA", "GJ", "HR", "HP", "JK", "JH", "KA", "KL",
    "LD", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB",
    "PY", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB",
}

def parse_cin(cin: str) -> dict | None:
    """Split a CIN into parts. Returns None if the format is invalid."""
    m = _CIN_RE.match((cin or "").strip().upper())
    if not m:
        return None

    listing, industry, state, year, ownership, serial = m.groups()

    if state not in _VALID_CIN_STATE_CODES:
        return None

    return {
        "listing_status": "Listed" if listing == "L" else "Unlisted",
        "nic_code": industry,
        "state_code": state,
        "incorporation_year": int(year),
        "ownership_code": ownership,
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
        "date_of_registration",
        "dateofregistration",
        "company_registration_date",
        "registration_date",
        "date_of_incorporation",
        "companyregistrationdate_date",
    ],
    "roc": ["company_roc_code", "roc_code", "roc", "rocname", "companyroccode"],
    "class": ["company_class", "companyclass"],
    "category": ["company_category", "companycategory"],
    "authorized_capital": [
        "authorized_cap",
        "authorized_capital",
        "authorised_capital",
        "authorizedcapital",
    ],
    "paidup_capital": ["paidup_capital", "paid_up_capital", "paidupcapital"],
    "listing_status": [
        "listing_status",
        "whether_listed_or_not",
        "listingstatus",
    ],
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
    url = f"{settings.DATA_GOV_BASE_URL.rstrip('/')}/{resource_id}"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.data.gov.in/",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/155.0.0.0 Safari/537.36"
        ),
    }

    try:
        resp = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.MCA_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, dict):
            raise MCAApiError("Unexpected API response format")

        if data.get("status") != "ok":
            raise MCAApiError(
                f"Unexpected API status: {data.get('status')!r}"
            )

        records = data.get("records", [])

        if records is None:
            return []

        if not isinstance(records, list):
            raise MCAApiError("Unexpected API records format")

        if not all(isinstance(record, dict) for record in records):
            raise MCAApiError("Unexpected record format")

        return records
    except MCAApiError:
        raise
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
    Search MCA records using candidate company-name variations.

    Returns:
      {
          "status": "found" | "not_found" | "error",
          "matches": [mapped records],
          "tried": [names],
          "errors": [...]
      }
    """
    if not isinstance(name, str) or not name.strip():
        return {
            "status": "invalid_input",
            "matches": [],
            "tried": [],
            "errors": [],
        }

    tried = []
    matches = []
    errors = []
    seen = set()

    for candidate in candidate_names(name):
        tried.append(candidate)

        try:
            records, search_errors = _search(
                {settings.MCA_NAME_FIELD: candidate}
            )
            errors.extend(search_errors)
        except MCAApiError as exc:
            errors.append(str(exc))
            continue

        for record in records:
            mapped = map_record(record)

            # Prefer CIN as the record identity. If it is missing,
            # fall back to normalized name and status.
            cin = str(mapped.get("cin") or "").strip().upper()
            company = normalize_name(str(mapped.get("name") or ""))
            status_value = str(mapped.get("status") or "").strip().upper()

            identity = (
                ("cin", cin)
                if cin
                else ("name_status", company, status_value)
            )

            if identity == ("name_status", "", ""):
                # Do not accidentally merge unrelated records
                # that have no usable identity.
                identity = ("unidentified", len(matches), candidate)

            if identity not in seen:
                seen.add(identity)
                matches.append(mapped)

    if matches:
        status = "found"
    elif errors:
        status = "error"
    else:
        status = "not_found"

    return {
        "status": status,
        "matches": matches,
        "tried": tried,
        "errors": errors,
    }



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


