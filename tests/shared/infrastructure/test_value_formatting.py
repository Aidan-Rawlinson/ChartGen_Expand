"""
Tests for shared/infrastructure/value_formatting.py

Display formatting only: "Values are not rescaled -- this only controls
display." That is the thing worth protecting. A percentage arrives already
expressed as a percentage, so a well-meaning multiply-by-100 here would put
every percentage in every report out by two orders of magnitude, and would
look entirely plausible in the code.

The other reason these matter: the Base Chart files carry their own copy of
this logic, because they import nothing from ChartGen. If the two ever
disagree, a chart's own axis labels stop matching the summary-stats table
printed beside it.
"""

from chartgen.shared.infrastructure.value_formatting import (
    format_number,
    format_reference_value,
)


# ---------------------------------------------------------------------------
# format_number
# ---------------------------------------------------------------------------

def test_a_plain_number_gets_thousands_separators_and_no_decimals():
    assert format_number(1234567, None) == "1,234,567"


def test_decimals_are_rounded_away_for_display():
    assert format_number(1234.7, None) == "1,235"


def test_the_percent_modifier_adds_a_suffix_without_rescaling_the_value():
    """
    45.0 means 45%, not 4500%. Nothing here multiplies by 100.
    """
    assert format_number(45.0, "P") == "45%"


def test_the_currency_modifier_adds_a_pound_prefix():
    assert format_number(1234.0, "C") == "£1,234"


def test_none_formats_as_blank_rather_than_as_zero():
    """
    "No data" and zero are different facts throughout ChartGen, and a
    report must not present the first as the second.
    """
    assert format_number(None, None) == ""
    assert format_number(None, "P") == ""
    assert format_number(None, "C") == ""


def test_zero_formats_as_zero_and_not_as_blank():
    assert format_number(0, None) == "0"


def test_an_unrecognised_modifier_falls_back_to_plain_formatting():
    assert format_number(1234.0, "Z") == "1,234"


def test_negative_numbers_keep_their_sign():
    assert format_number(-1234.0, None) == "-1,234"


# ---------------------------------------------------------------------------
# format_reference_value
# ---------------------------------------------------------------------------

def test_a_count_is_always_a_plain_integer_whatever_the_modifier():
    """
    A count of units is a count, even on a chart whose values are money or
    percentages. "£12" units would be nonsense.
    """
    assert format_reference_value(12, "count", "C") == "12"
    assert format_reference_value(12, "count", "P") == "12"


def test_a_percent_kind_is_shown_as_a_percentage_regardless_of_the_modifier():
    """
    Some reference rows are inherently percentages (a proportion of units
    meeting something) even when the underlying chart is in pounds.
    """
    assert format_reference_value(45.67, "percent", "C") == "45.7%"


def test_a_percent_kind_keeps_one_decimal_place():
    assert format_reference_value(45.0, "percent", None) == "45.0%"


def test_a_value_kind_follows_the_shape_s_own_modifier():
    assert format_reference_value(1234.0, "value", "C") == "£1,234"
    assert format_reference_value(45.0, "value", "P") == "45%"
    assert format_reference_value(1234.0, "value", None) == "1,234"


def test_a_missing_reference_value_formats_as_blank_for_every_kind():
    for kind in ["count", "percent", "value"]:
        assert format_reference_value(None, kind, None) == ""
