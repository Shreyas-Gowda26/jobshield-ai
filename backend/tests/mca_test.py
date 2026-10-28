
from unittest.mock import patch

from tools.registry.mca_lookup_tool import lookup_company


@patch("tools.registry.mca_lookup_tool._search")
def test_company_match_preserved_when_another_resource_fails(mock_search):
    mock_search.side_effect = [
        (
            [
                {
                    "CompanyName": "Example Technologies Private Limited",
                    "CIN": "U12345KA2020PTC123456",
                    "CompanyStatus": "Active",
                }
            ],
            ["resource_2: MCA API timeout"],
        ),
        (
            [],
            ["resource_3: MCA API unavailable"],
        ),
        (
            [],
            [],
        ),
        (
            [],
            [],
        ),
    ]

    result = lookup_company("Example Technologies Private Limited")

    assert result["status"] == "found"
    assert len(result["matches"]) == 1
    assert result["matches"][0]["name"] == (
        "Example Technologies Private Limited"
    )
    assert result["errors"]


import requests
from unittest.mock import patch
import pytest
from tools.registry.mca_lookup_tool import (
    _query,
    MCAApiError,
)


@patch("tools.registry.mca_lookup_tool.requests.get")
def test_mca_request_timeout_raises_mca_api_error(mock_get):
    mock_get.side_effect = requests.Timeout("Request timed out")

    with pytest.raises(MCAApiError, match="Timeout"):
        _query(
            resource_id="test-resource",
            filters={"company_name": "Example Technologies"},
        )

    mock_get.assert_called_once()



import pytest
from unittest.mock import Mock, patch

from tools.registry.mca_lookup_tool import _query, MCAApiError


def _mock_response(payload=None, json_error=None):
    response = Mock()
    response.raise_for_status.return_value = None

    if json_error:
        response.json.side_effect = json_error
    else:
        response.json.return_value = payload

    return response


@patch("tools.registry.mca_lookup_tool.requests.get")
def test_mca_invalid_json_is_wrapped(mock_get):
    mock_get.return_value = _mock_response(
        json_error=ValueError("Invalid JSON")
    )

    with pytest.raises(MCAApiError):
        _query("test-resource", {"company_name": "Example"})


@pytest.mark.parametrize("payload", [
    [],
    "unexpected response",
    123,
])
@patch("tools.registry.mca_lookup_tool.requests.get")
def test_mca_unexpected_response_type_is_handled(mock_get, payload):
    mock_get.return_value = _mock_response(payload=payload)

    with pytest.raises(MCAApiError):
        _query("test-resource", {"company_name": "Example"})


@patch("tools.registry.mca_lookup_tool.requests.get")
def test_mca_missing_status_is_rejected(mock_get):
    mock_get.return_value = _mock_response(
        payload={"records": []}
    )

    with pytest.raises(MCAApiError):
        _query("test-resource", {"company_name": "Example"})


@patch("tools.registry.mca_lookup_tool.requests.get")
def test_mca_missing_records_returns_empty_list(mock_get):
    mock_get.return_value = _mock_response(
        payload={"status": "ok"}
    )

    result = _query("test-resource", {"company_name": "Example"})

    assert result == []


from unittest.mock import patch, call

from tools.registry.mca_lookup_tool import lookup_company,settings


def test_lookup_company_rejects_empty_name():
    result = lookup_company("   ")

    assert result["status"] == "invalid_input"
    assert result["matches"] == []
    assert result["tried"] == []
    assert result["errors"] == []


@patch("tools.registry.mca_lookup_tool._search")
def test_lookup_company_empty_results_are_not_found(mock_search):
    mock_search.return_value = ([], [])

    result = lookup_company("Example Technologies")

    assert result["status"] == "not_found"
    assert result["matches"] == []
    assert result["tried"]
    assert result["errors"] == []


@patch("tools.registry.mca_lookup_tool._search")
def test_lookup_company_deduplicates_same_cin(mock_search):
    record = {
        "CompanyName": "Example Technologies Private Limited",
        "CIN": "U12345KA2020PTC123456",
        "CompanyStatus": "Active",
    }
    mock_search.return_value = ([record, record.copy()], [])

    result = lookup_company("Example Technologies")

    assert result["status"] == "found"
    assert len(result["matches"]) == 1


@patch("tools.registry.mca_lookup_tool._search")
def test_lookup_company_preserves_distinct_cins(mock_search):
    records = [
        {
            "CompanyName": "Example Technologies Private Limited",
            "CIN": "U12345KA2020PTC123456",
            "CompanyStatus": "Active",
        },
        {
            "CompanyName": "Example Technologies Limited",
            "CIN": "U12345KA2021PTC123457",
            "CompanyStatus": "Active",
        },
    ]
    mock_search.return_value = (records, [])

    result = lookup_company("Example Technologies")

    assert result["status"] == "found"
    assert len(result["matches"]) == 2



@patch("tools.registry.mca_lookup_tool._search")
def test_lookup_company_records_candidate_variations(mock_search):
    mock_search.return_value = ([], [])

    result = lookup_company("Example Technologies Private Limited")

    assert result["tried"]
    assert len(result["tried"]) == len(set(result["tried"]))
    assert mock_search.call_count == len(result["tried"])

    searched_filters = [
        item.args[0]
        for item in mock_search.call_args_list
    ]

    assert all(
        settings.MCA_NAME_FIELD in filters
        for filters in searched_filters
    )

    searched_names = [
        filters[settings.MCA_NAME_FIELD]
        for filters in searched_filters
    ]

    assert searched_names == result["tried"]



import pytest
from unittest.mock import patch

from tools.registry.mca_lookup_tool import lookup_cin


def test_lookup_cin_rejects_empty_cin():
    with patch(
        "tools.registry.mca_lookup_tool._search"
    ) as mock_search:
        result = lookup_cin("")

    assert result["status"] == "invalid_format"
    assert result["cin"] == ""
    assert result["matches"] == []
    assert result["errors"] == []
    mock_search.assert_not_called()


def test_lookup_cin_normalizes_cin_before_search():
    # Replace this with a CIN that parse_cin() accepts
    # in your project.
    valid_cin = "L17110KA1988PLC009162"

    with patch(
        "tools.registry.mca_lookup_tool._search"
    ) as mock_search:
        mock_search.return_value = ([{"company": "Example"}], [])
        with patch(
            "tools.registry.mca_lookup_tool.parse_cin",
            return_value={"valid": True},
        ):
            result = lookup_cin(f"  {valid_cin.lower()}  ")

    assert result["cin"] == valid_cin
    assert result["status"] == "found"
    mock_search.assert_called_once()


def test_lookup_cin_handles_api_exception():
    valid_cin = "L17110KA1988PLC009162"

    with (
        patch(
            "tools.registry.mca_lookup_tool.parse_cin",
            return_value={"valid": True},
        ),
        patch(
            "tools.registry.mca_lookup_tool._search",
            side_effect=Exception("unexpected failure"),
        ),
    ):
        # This test deliberately checks the current exception contract.
        # The function only catches MCAApiError, so an unexpected
        # exception currently propagates.
        with pytest.raises(Exception, match="unexpected failure"):
            lookup_cin(valid_cin)


def test_lookup_cin_reports_mca_api_error():
    valid_cin = "L17110KA1988PLC009162"

    with (
        patch(
            "tools.registry.mca_lookup_tool.parse_cin",
            return_value={"valid": True},
        ),
        patch(
            "tools.registry.mca_lookup_tool._search",
            side_effect=__import__(
                "tools.registry.mca_lookup_tool",
                fromlist=["MCAApiError"],
            ).MCAApiError("MCA unavailable"),
        ),
    ):
        result = lookup_cin(valid_cin)

    assert result["status"] == "error"
    assert result["cin"] == valid_cin
    assert result["matches"] == []
    assert "MCA unavailable" in result["errors"][0]


def test_lookup_cin_returns_not_found_when_no_records_or_errors():
    valid_cin = "L17110KA1988PLC009162"

    with (
        patch(
            "tools.registry.mca_lookup_tool.parse_cin",
            return_value={"valid": True},
        ),
        patch(
            "tools.registry.mca_lookup_tool._search",
            return_value=([], []),
        ),
    ):
        result = lookup_cin(valid_cin)

    assert result["status"] == "not_found"
    assert result["matches"] == []
    assert result["errors"] == []


def test_lookup_cin_returns_error_when_no_records_and_search_errors():
    valid_cin = "L17110KA1988PLC009162"

    with (
        patch(
            "tools.registry.mca_lookup_tool.parse_cin",
            return_value={"valid": True},
        ),
        patch(
            "tools.registry.mca_lookup_tool._search",
            return_value=([], ["MCA resource unavailable"]),
        ),
    ):
        result = lookup_cin(valid_cin)

    assert result["status"] == "error"
    assert result["matches"] == []
    assert result["errors"] == ["MCA resource unavailable"]


from unittest.mock import patch

from tools.registry.mca_lookup_tool import lookup_company


def test_lookup_company_deduplicates_records_without_cin():
    records = [
        {"name": "Example Test Company Ltd", "status": "Active"},
        {"name": " example test company ltd ", "status": " active "},
    ]

    with patch(
        "tools.registry.mca_lookup_tool.candidate_names",
        return_value=["Example Test Company"],
    ), patch(
        "tools.registry.mca_lookup_tool._search",
        return_value=(records, []),
    ):
        result = lookup_company("Example Test Company")

    assert result["status"] == "found"
    assert len(result["matches"]) == 1


import pytest

from tools.registry.mca_lookup_tool import parse_cin


def test_parse_cin_valid_unlisted_company():
    result = parse_cin("U17110KA1988PLC009162")

    assert result is not None
    assert result["listing_status"] == "Unlisted"
    assert result["nic_code"] == "17110"
    assert result["state_code"] == "KA"
    assert result["incorporation_year"] == 1988
    assert result["ownership_code"] == "PLC"
    assert result["serial"] == "009162"


def test_parse_cin_normalizes_lowercase_and_whitespace():
    result = parse_cin("  l17110ka1988plc009162  ")

    assert result is not None
    assert result["listing_status"] == "Listed"
    assert result["state_code"] == "KA"


@pytest.mark.parametrize(
    "cin",
    [
        "",
        "   ",
        "INVALID",
        "L17110KA1988PLC00916",    # Serial too short
        "L17110KA1988PLC009162X",  # Extra character
        "X17110KA1988PLC009162",   # Invalid listing prefix
        "L17110ZZ1988PLC009162",   # Invalid state code, if regex enforces it
    ],
)
def test_parse_cin_rejects_invalid_format(cin):
    assert parse_cin(cin) is None
