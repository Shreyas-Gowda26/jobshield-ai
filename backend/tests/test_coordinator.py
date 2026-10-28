from unittest.mock import patch

from backend.agents.coordinator import run_verification


@patch("backend.agents.coordinator.save_verification")
@patch("backend.agents.coordinator.lookup_domain")
@patch("backend.agents.coordinator.search_company_presence")
@patch("backend.agents.coordinator.lookup_company")
def test_api_errors_do_not_increase_risk(
    mock_mca,
    mock_search,
    mock_whois,
    mock_save,
):
    mock_mca.return_value = {
        "status": "error",
        "matches": [],
        "errors": ["Simulated timeout"],
    }
    mock_search.return_value = {
        "status": "error",
        "results": [],
        "error": "Simulated search failure",
    }
    mock_whois.return_value = {
        "status": "error",
        "domain": "example.com",
        "error": "Simulated WHOIS failure",
    }
    mock_save.return_value = {
        "status": "saved",
        "verification_id": "test-id",
        "error": None,
    }

    result = run_verification(
        company_name="Example Test Company",
        website="example.com",
    )

    assert result["status"] == "completed"
    assert result["scoring"]["risk_score"] == 0
    assert result["scoring"]["risk_level"] == "no_flags_detected"
    assert result["checks"]["mca_company"]["status"] == "error"
    assert result["checks"]["web_presence"]["status"] == "error"
    assert result["checks"]["domain_registration"]["status"] == "error"
    mock_save.assert_called_once()

    print("PASS: API errors do not increase risk.")
    print("Risk score:", result["scoring"]["risk_score"])


@patch("backend.agents.coordinator.save_verification")
@patch("backend.agents.coordinator.scan_offer")
@patch("backend.agents.coordinator.search_company_presence")
@patch("backend.agents.coordinator.lookup_company")
def test_offer_findings_affect_risk_score(
    mock_mca,
    mock_search,
    mock_scan,
    mock_save,
):
    mock_mca.return_value = {
        "status": "error",
        "matches": [],
        "errors": ["Simulated timeout"],
    }
    mock_search.return_value = {
        "status": "error",
        "results": [],
        "error": "Simulated search failure",
    }
    mock_scan.return_value = {
        "status": "scanned",
        "findings": [
            {
                "rule_id": "SENSITIVE_CREDENTIAL_REQUEST",
                "category": "sensitive_information",
                "severity": "high",
                "evidence": "Requests a bank PIN",
                "recommendation": "Never share banking credentials",
            },
            {
                "rule_id": "UPFRONT_PAYMENT",
                "category": "payment_request",
                "severity": "medium",
                "evidence": "Requests an application fee",
                "recommendation": "Verify the employer independently",
            },
        ],
        "findings_count": 2,
        "severity_counts": {"high": 1, "medium": 1, "low": 0},
        "error": None,
    }
    mock_save.return_value = {
        "status": "saved",
        "verification_id": "test-id",
        "error": None,
    }

    result = run_verification(
        company_name="Example Test Company",
        offer_text="Mock suspicious offer",
    )

    assert result["scoring"]["risk_score"] == 37
    assert result["scoring"]["risk_level"] == "medium"
    assert len(result["scoring"]["findings_considered"]) == 2
    mock_save.assert_called_once()

    print("PASS: Offer findings affect the risk score.")
    print("Risk score:", result["scoring"]["risk_score"])


@patch("backend.agents.coordinator.save_verification")
@patch("backend.agents.coordinator.search_company_presence")
@patch("backend.agents.coordinator.lookup_cin")
@patch("backend.agents.coordinator.lookup_company")
def test_cin_lookup_failure_does_not_stop_verification(
    mock_mca,
    mock_cin,
    mock_search,
    mock_save,
):
    mock_mca.return_value = {
        "status": "found",
        "matches": [{"name": "Example Test Company"}],
        "errors": [],
    }
    mock_cin.return_value = {
        "status": "error",
        "matches": [],
        "errors": ["Simulated CIN lookup failure"],
    }
    mock_search.return_value = {
        "status": "success",
        "results": [],
    }
    mock_save.return_value = {
        "status": "saved",
        "verification_id": "test-id",
        "error": None,
    }

    result = run_verification(
        company_name="Example Test Company",
        cin="L85110KA1981PLC013115",
    )

    assert result["status"] == "completed"
    assert result["checks"]["mca_cin"]["status"] == "error"
    assert "web_presence" in result["checks"]
    assert result["scoring"]["risk_score"] == 0
    mock_search.assert_called_once()
    mock_save.assert_called_once()


from backend.agents.coordinator import _summarize_company_identity


def test_company_identity_single_match():
    result = _summarize_company_identity({
        "status": "found",
        "matches": [{"name": "Example Private Limited"}],
    })

    assert result["status"] == "single_match"
    assert result["matches_count"] == 1


def test_company_identity_multiple_matches():
    result = _summarize_company_identity({
        "status": "found",
        "matches": [
            {"name": "Example Private Limited"},
            {"name": "Example Technologies Limited"},
        ],
    })

    assert result["status"] == "multiple_matches"
    assert result["matches_count"] == 2


def test_company_identity_not_found():
    result = _summarize_company_identity({
        "status": "not_found",
        "matches": [],
    })

    assert result["status"] == "not_found"


def test_company_identity_lookup_error():
    result = _summarize_company_identity({
        "status": "error",
        "matches": [],
        "errors": ["MCA API unavailable"],
    })

    assert result["status"] == "lookup_error"


import pytest
from unittest.mock import patch

from backend.agents.coordinator import run_verification


@pytest.mark.parametrize(
    "company_name",
    ["", "   ", "\t\n"],
)
def test_empty_company_name_is_rejected(company_name):
    with patch(
        "backend.agents.coordinator.lookup_company"
    ) as mock_mca:
        result = run_verification(company_name=company_name)

    assert result["status"] == "invalid_input"
    assert result["error"] == "A non-empty company name is required"
    mock_mca.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cin", 123),
        ("website", None),
        ("offer_text", ["not", "a", "string"]),
    ],
)
def test_invalid_optional_input_types_are_rejected(field, value):
    kwargs = {
        "company_name": "Example Test Company",
        field: value,
    }

    with patch(
        "backend.agents.coordinator.lookup_company"
    ) as mock_mca:
        result = run_verification(**kwargs)

    assert result["status"] == "invalid_input"
    assert f"{field} must be a string" == result["error"]
    mock_mca.assert_not_called()


@patch("backend.agents.coordinator.save_verification")
@patch("backend.agents.coordinator.search_company_presence")
@patch("backend.agents.coordinator.lookup_company")
def test_persistence_failure_does_not_erase_verification(
    mock_mca,
    mock_search,
    mock_save,
):
    mock_mca.return_value = {
        "status": "found",
        "matches": [{"name": "Example Test Company"}],
        "errors": [],
    }
    mock_search.return_value = {
        "status": "success",
        "results": [],
    }
    mock_save.side_effect = RuntimeError("Database unavailable")

    result = run_verification(
        company_name="Example Test Company",
    )

    assert result["status"] == "completed"
    assert result["company_name"] == "Example Test Company"
    assert "checks" in result
    assert "scoring" in result

    assert result["history"]["status"] == "error"
    assert "Database unavailable" in result["history"]["error"]

    mock_save.assert_called_once()


@patch("backend.agents.coordinator.save_verification")
@patch("backend.agents.coordinator.search_company_presence")
@patch("backend.agents.coordinator.lookup_company")
def test_successful_persistence_is_reported(
    mock_mca,
    mock_search,
    mock_save,
):
    mock_mca.return_value = {
        "status": "found",
        "matches": [{"name": "Example Test Company"}],
        "errors": [],
    }
    mock_search.return_value = {
        "status": "success",
        "results": [],
    }
    mock_save.return_value = {
        "status": "saved",
        "verification_id": "test-id",
        "error": None,
    }

    result = run_verification(
        company_name="Example Test Company",
    )

    assert result["status"] == "completed"
    assert result["history"]["status"] == "saved"
    assert result["history"]["verification_id"] == "test-id"
    mock_save.assert_called_once()



from unittest.mock import patch

from backend.agents.coordinator import run_verification


@patch("backend.agents.coordinator.save_verification")
@patch("backend.agents.coordinator.search_company_presence")
@patch("backend.agents.coordinator.lookup_company")
def test_partial_mca_failure_preserves_match_and_error(
    mock_mca,
    mock_search,
    mock_save,
):
    mock_mca.return_value = {
        "status": "found",
        "matches": [
            {
                "name": "Example Test Company",
                "cin": "L17110KA1988PLC009162",
                "status": "Active",
            }
        ],
        "errors": ["One MCA resource was unavailable"],
    }
    mock_search.return_value = {
        "status": "success",
        "results": [],
    }
    mock_save.return_value = {"status": "saved"}

    result = run_verification(
        company_name="Example Test Company",
    )

    assert result["status"] == "completed"
    assert result["checks"]["mca_company"]["status"] == "found"
    assert len(result["checks"]["mca_company"]["matches"]) == 1
    assert result["checks"]["mca_company"]["errors"] == [
        "One MCA resource was unavailable"
    ]

    # A match should not be discarded just because a resource failed.
    assert result["company_identity"]["status"] == "single_match"


from backend.agents.coordinator import _summarize_company_identity


def test_company_identity_reports_partial_failure_with_match():
    result = _summarize_company_identity({
        "status": "found",
        "matches": [{"name": "Example Company"}],
        "errors": ["One resource failed"],
    })

    assert result["status"] == "single_match"
    assert result["matches_count"] == 1
    assert result["partial_failure"] is True
    assert "incomplete" in result["message"]


def test_company_identity_reports_no_partial_failure_when_clean():
    result = _summarize_company_identity({
        "status": "found",
        "matches": [{"name": "Example Company"}],
        "errors": [],
    })

    assert result["status"] == "single_match"
    assert result["partial_failure"] is False
