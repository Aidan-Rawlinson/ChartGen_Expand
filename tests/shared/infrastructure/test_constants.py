"""
Tests for shared/infrastructure/constants.py

coerce_row exists because everything in a workfile arrives from a CSV or a
spreadsheet, where types are whatever the file happened to hold. Two things
follow from that and both matter.

Ids are forced to strings. Unit ids are compared as strings throughout
ChartGen (population_layers.py says so explicitly), so a unit_id that
arrives as the integer 1 and is compared against the string "1" silently
fails to match, and the unit quietly drops out of a population layer with
nothing raising.

The enabled column is forced to 1 or 0. It arrives as "1", "true", True or
an empty cell depending on where it came from, and batch_process decides
whether to run a row on it.
"""

from chartgen.shared.infrastructure.constants import (
    FIELD_TYPES,
    SPINE_COLUMN_ORDER,
    coerce_row,
)


# ---------------------------------------------------------------------------
# Ids become strings
# ---------------------------------------------------------------------------

def test_an_id_read_as_a_number_becomes_a_string():
    """
    The failure this prevents: 1 != "1", so the unit stops matching and
    disappears from its population layer without any error.
    """
    assert coerce_row({"unit_id": 1})["unit_id"] == "1"


def test_an_id_that_is_already_a_string_is_left_alone():
    assert coerce_row({"unit_id": "u1"})["unit_id"] == "u1"


def test_a_missing_id_becomes_an_empty_string_not_the_word_none():
    """
    "None" would be a perfectly valid-looking id that matches nothing.
    """
    assert coerce_row({"unit_id": None})["unit_id"] == ""


def test_every_id_column_is_coerced_the_same_way():
    coerced = coerce_row({"unit_id": 1, "submission_id": 2, "organisation_id": 3})
    assert coerced == {"unit_id": "1", "submission_id": "2", "organisation_id": "3"}


# ---------------------------------------------------------------------------
# enabled becomes 1 or 0
# ---------------------------------------------------------------------------

def test_the_recognised_true_values_all_become_one():
    for raw in ["1", 1, "true", "True", True, "yes"]:
        assert coerce_row({"enabled": raw})["enabled"] == 1, raw


def test_anything_else_becomes_zero():
    for raw in ["0", 0, "", "false", "False", None, "maybe"]:
        assert coerce_row({"enabled": raw})["enabled"] == 0, raw


def test_enabled_is_a_number_not_a_string():
    """
    Stored as 1/0 rather than "1"/"0" so a row is never enabled purely
    because a non-empty string is truthy.
    """
    assert isinstance(coerce_row({"enabled": "1"})["enabled"], int)
    assert isinstance(coerce_row({"enabled": "no"})["enabled"], int)


# ---------------------------------------------------------------------------
# Columns not in the field-type map
# ---------------------------------------------------------------------------

def test_a_column_that_is_not_listed_is_left_exactly_as_it_was():
    """
    coerce_row is a targeted coercion, not a general cleanup. A population
    table can hold any columns at all, and their values are the user's.
    """
    row = {"unit_id": 1, "Region()": "North", "some_number": 42, "blank": None}
    coerced = coerce_row(row)
    assert coerced["Region()"] == "North"
    assert coerced["some_number"] == 42
    assert coerced["blank"] is None


def test_a_column_that_is_absent_is_not_invented():
    """Coercing a row must not add keys the row never had."""
    assert coerce_row({"unit_id": 1}) == {"unit_id": "1"}


def test_the_row_is_changed_in_place_and_also_returned():
    """
    Documented as coercing in place. Callers rely on both, so a change to
    return a copy instead would silently stop updating the caller's row.
    """
    row = {"unit_id": 1}
    returned = coerce_row(row)
    assert returned is row
    assert row["unit_id"] == "1"


# ---------------------------------------------------------------------------
# The population-table spine
# ---------------------------------------------------------------------------

def test_the_spine_columns_are_in_authoring_order():
    """
    Read by both the UI's column display order and the Excel round-trip's
    export/import order, so the two cannot drift. Reordering this list
    reorders the spreadsheet a user gets.
    """
    assert SPINE_COLUMN_ORDER == ["unit_id", "unit_code", "unit_name", "soft_parents"]


def test_the_id_columns_are_all_declared_as_strings():
    for column in ["unit_id", "submission_id", "organisation_id"]:
        assert FIELD_TYPES[column] is str
