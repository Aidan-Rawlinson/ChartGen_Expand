"""
Tests for shared/infrastructure/period_ids.py

The rule these protect, from the root CLAUDE.md: "Stored values are never
rewritten. A value the user picked or typed stays exactly as they left it."

period_ids.py is where that rule is most easily broken by accident, because
a stored period is a composite string ("July 2025(1338)") and the code
constantly needs the bare id out of it. If extraction and rebuilding ever
stop being exact inverses, a report's period range silently shifts or loses
its label, with nothing raising anywhere.
"""

from chartgen.shared.infrastructure.period_ids import (
    build_metric_periods_string,
    build_period_display,
    extract_metric_period_ids,
    extract_period_id,
    extract_period_label,
    parse_metric_periods_string,
)


# ---------------------------------------------------------------------------
# extract_period_id
# ---------------------------------------------------------------------------

def test_the_id_is_taken_from_inside_the_brackets():
    assert extract_period_id("July 2025(1338)") == "1338"


def test_a_bare_id_with_no_label_comes_back_unchanged():
    assert extract_period_id("1338") == "1338"


def test_a_blank_value_gives_a_blank_id():
    assert extract_period_id("") == ""
    assert extract_period_id(None) == ""


def test_a_whole_number_float_from_excel_loses_its_decimal_point():
    """
    openpyxl hands back a bare id typed into a cell as a float, so "1338"
    arrives as 1338.0. Left alone it would become the id "1338.0", which
    matches no period on any shape.
    """
    assert extract_period_id(1338.0) == "1338"


def test_a_label_containing_brackets_does_not_confuse_the_extraction():
    """Only the final bracketed group is the id."""
    assert extract_period_id("Q1 (provisional)(1338)") == "1338"


def test_surrounding_whitespace_is_ignored():
    assert extract_period_id("  July 2025(1338)  ") == "1338"


# ---------------------------------------------------------------------------
# build_period_display, and the inverse relationship
# ---------------------------------------------------------------------------

def test_a_known_label_is_stored_alongside_the_id():
    assert build_period_display("1338", "July 2025") == "July 2025(1338)"


def test_an_id_with_no_known_label_is_stored_bare():
    assert build_period_display("1338") == "1338"


def test_a_blank_id_stores_nothing_even_if_a_label_is_known():
    assert build_period_display("", "July 2025") == ""


def test_building_then_extracting_returns_the_original_id():
    """
    The documented inverse relationship, which is the whole point of the
    module. Checked with and without a label, since the stored form differs.
    """
    for period_id, label in [("1338", "July 2025"), ("1338", ""), ("9", "Q4 2024/25")]:
        assert extract_period_id(build_period_display(period_id, label)) == period_id


# ---------------------------------------------------------------------------
# extract_period_label
# ---------------------------------------------------------------------------

def test_the_label_is_taken_from_before_the_brackets():
    assert extract_period_label("July 2025(1338)") == "July 2025"


def test_a_bare_id_has_no_label():
    assert extract_period_label("1338") == ""


def test_extracting_a_label_from_nothing_gives_nothing():
    assert extract_period_label("") == ""
    assert extract_period_label(None) == ""


# ---------------------------------------------------------------------------
# The '^'-delimited metric_periods list
# ---------------------------------------------------------------------------

def test_metric_periods_split_on_the_caret():
    assert parse_metric_periods_string("1338^1339^1340") == ["1338", "1339", "1340"]


def test_an_empty_metric_periods_string_is_an_empty_list():
    assert parse_metric_periods_string("") == []


def test_empty_segments_between_carets_are_dropped():
    assert parse_metric_periods_string("1338^^1339") == ["1338", "1339"]


def test_metric_periods_keep_the_order_they_were_given():
    """
    Order is meaningful: it becomes the order of the metric-series on the
    converted shape, and so the order of the bars on the chart.
    """
    assert build_metric_periods_string(["1340", "1338", "1339"]) == "1340^1338^1339"


def test_a_metric_periods_round_trip_preserves_order_and_content():
    ids = ["1340", "1338", "1339"]
    assert parse_metric_periods_string(build_metric_periods_string(ids)) == ids


def test_labelled_metric_periods_reduce_to_bare_ids_in_order():
    """
    extract_metric_period_ids is the list-wide equivalent of
    extract_period_id: it takes whatever was stored, in whatever mix of
    forms, and produces something ready for prepare_chart_cut.
    """
    stored = "July 2025(1338)^1339^August 2025(1340)"
    assert extract_metric_period_ids(stored) == "1338^1339^1340"


def test_extracting_ids_from_an_empty_metric_periods_string_gives_nothing():
    assert extract_metric_period_ids("") == ""
    assert extract_metric_period_ids(None) == ""
