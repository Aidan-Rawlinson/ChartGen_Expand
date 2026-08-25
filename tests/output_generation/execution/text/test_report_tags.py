"""
test_report_tags.py
The report level text tags: the two date formats, and the promise
REPORT_TEXT_TAGS makes — that it is the one definition every surface reads,
so an entry present here works and an entry removed stops working.
"""

from datetime import date

import pytest

from chartgen.output_generation.execution.text.report_tags import (
    REPORT_TEXT_TAGS, build_report_tag_tokens, _format_date, _format_month,
)


class _StubReportContext:
    """ReportContext's shape, without importing the dataclass."""

    def __init__(self, unit_name, unit_code="ABC"):
        self.unit_id = "1"
        self.unit_code = unit_code
        self.unit_name = unit_name


# --- Date formats ---

def test_format_date_single_digit_day_has_no_leading_zero():
    assert _format_date(date(2026, 8, 5)) == "5 August 2026"


def test_format_date_double_digit_day():
    assert _format_date(date(2026, 8, 25)) == "25 August 2026"


def test_format_date_first_of_january():
    assert _format_date(date(2027, 1, 1)) == "1 January 2027"


def test_format_month_is_month_name_and_year():
    assert _format_month(date(2026, 8, 5)) == "August 2026"
    assert _format_month(date(2026, 12, 31)) == "December 2026"


# --- Token building ---

def test_date_and_month_resolve_without_a_reporting_unit():
    """
    Neither depends on the reporting unit, so both resolve with no
    ReportContext at all. The unit name tag, which does depend on one, is
    omitted so its literal text survives in the deck.
    """
    tokens = build_report_tag_tokens(None)

    today = date.today()
    assert tokens["[date]"] == _format_date(today)
    assert tokens["[month]"] == _format_month(today)
    assert "[selected-reporting-unit-name]" not in tokens
    assert "[code]" not in tokens


def test_unit_name_and_code_resolve_from_the_report_context():
    tokens = build_report_tag_tokens(_StubReportContext("Example NHS Trust"))
    assert tokens["[selected-reporting-unit-name]"] == "Example NHS Trust"
    assert tokens["[code]"] == "ABC"


def test_empty_unit_name_replaces_with_empty_string_rather_than_being_omitted():
    """
    A ReportContext exists, so the tag is resolvable; the resolved value
    just happens to be blank. Omitting it would leave the literal tag text
    visible in the report instead.
    """
    tokens = build_report_tag_tokens(_StubReportContext("", unit_code=""))
    assert tokens["[selected-reporting-unit-name]"] == ""
    assert tokens["[code]"] == ""


def test_every_defined_tag_appears_in_the_tokens():
    """
    The one-definition promise: nothing in REPORT_TEXT_TAGS is display-only.
    With a ReportContext present, every entry resolves to a token.
    """
    tokens = build_report_tag_tokens(_StubReportContext("Example NHS Trust"))
    assert set(tokens) == {entry["tag"] for entry in REPORT_TEXT_TAGS}


# --- The list itself ---

@pytest.mark.parametrize("entry", REPORT_TEXT_TAGS, ids=lambda e: e["tag"])
def test_entry_is_well_formed(entry):
    """
    Both consuming surfaces read tag, description and resolve, so an entry
    added without one of them fails here rather than in the application.
    """
    assert entry["tag"].startswith("[") and entry["tag"].endswith("]")
    assert len(entry["tag"]) > 2
    assert entry["description"].strip()
    assert callable(entry["resolve"])


def test_tags_are_unique():
    tags = [entry["tag"] for entry in REPORT_TEXT_TAGS]
    assert len(tags) == len(set(tags))
