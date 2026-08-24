"""
Tests for shared/infrastructure/soft_parents.py

soft_parents links a row in one population table to rows in others, so that
ChartGen knows which rows represent the same real-world organisation across
different tables and years. resolve_full_unit_set is described as "the
single source of truth for which rows represent this same real-world unit in
each table", and a batch run uses it to decide which units count as
"Selected" on every chart.

Three documented rules are worth pinning:

  - "Resolution is one hop only. Nothing here follows a resolved row's own
    soft_parents onward to a second hop." Following a second hop would
    quietly widen "Selected" on every chart in a report.
  - Links are "recorded on the child side only; the linked-to table carries
    no reverse reference", which is why resolving in reverse needs to know
    the row's own table name.
  - "A table entry can hold more than one row, and both are expected to be
    highlighted. This is not a case to collapse to one." An obvious-looking
    simplification to one row per table would lose data.
"""

from chartgen.shared.infrastructure.soft_parents import (
    format_soft_parents,
    parse_soft_parents,
    resolve_all_related_rows,
    resolve_full_unit_set,
    resolve_referencing_rows,
    resolve_related_rows,
)


# ---------------------------------------------------------------------------
# The cell format
# ---------------------------------------------------------------------------

def test_one_link_to_one_table_formats_as_table_then_id():
    assert format_soft_parents({"nhs_organisations": ["n1"]}) == "nhs_organisations:n1"


def test_several_ids_in_one_table_are_joined_with_a_caret():
    assert format_soft_parents({"nhs_organisations": ["n1", "n2"]}) == "nhs_organisations:n1^n2"


def test_links_to_different_tables_are_separated_with_a_pipe():
    formatted = format_soft_parents({"table_a": ["a1"], "table_b": ["b1"]})
    assert formatted == "table_a:a1|table_b:b1"


def test_a_table_with_no_ids_is_left_out_entirely():
    """An empty list is not a link, and must not leave a dangling "name:" behind."""
    assert format_soft_parents({"table_a": ["a1"], "table_b": []}) == "table_a:a1"


def test_no_links_at_all_formats_as_an_empty_cell():
    assert format_soft_parents({}) == ""


def test_parsing_an_empty_cell_gives_no_links():
    assert parse_soft_parents("") == {}
    assert parse_soft_parents(None) == {}
    assert parse_soft_parents("   ") == {}


def test_formatting_then_parsing_returns_the_original_links():
    links = {"table_a": ["a1", "a2"], "table_b": ["b1"]}
    assert parse_soft_parents(format_soft_parents(links)) == links


def test_a_malformed_segment_with_no_colon_is_skipped_rather_than_crashing():
    """
    This cell is hand-editable via the Excel round-trip, so it will
    sometimes arrive damaged. One bad segment must not lose the good ones.
    """
    assert parse_soft_parents("table_a:a1|rubbish|table_b:b1") == {
        "table_a": ["a1"], "table_b": ["b1"],
    }


# ---------------------------------------------------------------------------
# Resolving forwards: the rows this row points at
# ---------------------------------------------------------------------------

def test_a_row_resolves_to_the_rows_its_own_links_point_at():
    child = {"unit_id": "s1", "soft_parents": "nhs_organisations:n1"}
    tables = {"nhs_organisations": [
        {"unit_id": "n1", "unit_name": "Alpha"},
        {"unit_id": "n2", "unit_name": "Bravo"},
    ]}
    resolved = resolve_related_rows(child, tables)
    assert list(resolved) == ["nhs_organisations"]
    assert [r["unit_id"] for r in resolved["nhs_organisations"]] == ["n1"]


def test_a_table_with_no_matching_row_is_omitted_rather_than_present_and_empty():
    child = {"unit_id": "s1", "soft_parents": "nhs_organisations:nope"}
    tables = {"nhs_organisations": [{"unit_id": "n1"}]}
    assert resolve_related_rows(child, tables) == {}


def test_a_link_to_a_table_that_does_not_exist_resolves_to_nothing():
    child = {"unit_id": "s1", "soft_parents": "deleted_table:n1"}
    assert resolve_related_rows(child, {"nhs_organisations": [{"unit_id": "n1"}]}) == {}


def test_resolution_does_not_follow_a_second_hop():
    """
    s1 links to n1, and n1 itself links to x1. Resolving s1 must reach n1
    and stop. Following the chain would silently widen the unit set.
    """
    child = {"unit_id": "s1", "soft_parents": "middle:n1"}
    tables = {
        "middle": [{"unit_id": "n1", "soft_parents": "far:x1"}],
        "far": [{"unit_id": "x1", "soft_parents": ""}],
    }
    resolved = resolve_related_rows(child, tables)
    assert list(resolved) == ["middle"]
    assert "far" not in resolved


# ---------------------------------------------------------------------------
# Resolving backwards: the rows that point at this row
# ---------------------------------------------------------------------------

def test_a_row_can_be_found_from_the_rows_that_reference_it():
    """
    The parent has nothing on it to search by, because links are recorded
    on the child side only. This is the direction that needs the parent's
    own table name.
    """
    parent = {"unit_id": "n1"}
    tables = {
        "nhs_organisations": [parent],
        "submissions_2026": [
            {"unit_id": "s1", "soft_parents": "nhs_organisations:n1"},
            {"unit_id": "s2", "soft_parents": "nhs_organisations:n2"},
        ],
    }
    resolved = resolve_referencing_rows(parent, "nhs_organisations", tables)
    assert [r["unit_id"] for r in resolved["submissions_2026"]] == ["s1"]


def test_a_row_does_not_find_itself_when_resolving_backwards():
    parent = {"unit_id": "n1", "soft_parents": ""}
    tables = {"nhs_organisations": [parent]}
    assert resolve_referencing_rows(parent, "nhs_organisations", tables) == {}


def test_two_rows_in_one_table_can_both_reference_the_same_row():
    """
    The "not a case to collapse to one" rule. Two submissions from the same
    organisation in one table are both real and both expected.
    """
    parent = {"unit_id": "n1"}
    tables = {
        "nhs_organisations": [parent],
        "submissions_2026": [
            {"unit_id": "s1", "soft_parents": "nhs_organisations:n1"},
            {"unit_id": "s2", "soft_parents": "nhs_organisations:n1"},
        ],
    }
    resolved = resolve_referencing_rows(parent, "nhs_organisations", tables)
    assert [r["unit_id"] for r in resolved["submissions_2026"]] == ["s1", "s2"]


# ---------------------------------------------------------------------------
# Both directions at once
# ---------------------------------------------------------------------------

def test_both_directions_are_combined_into_one_map():
    middle = {"unit_id": "m1", "soft_parents": "parents:p1"}
    tables = {
        "middles": [middle],
        "parents": [{"unit_id": "p1"}],
        "children": [{"unit_id": "c1", "soft_parents": "middles:m1"}],
    }
    resolved = resolve_all_related_rows(middle, "middles", tables)
    assert set(resolved) == {"parents", "children"}


def test_a_row_reachable_in_both_directions_appears_only_once():
    """
    A mutual link would otherwise produce the same row twice, and a
    duplicate in the unit set inflates every count on the chart.
    """
    row = {"unit_id": "a1", "soft_parents": "other:b1"}
    tables = {
        "own": [row],
        "other": [{"unit_id": "b1", "soft_parents": "own:a1"}],
    }
    resolved = resolve_all_related_rows(row, "own", tables)
    assert [r["unit_id"] for r in resolved["other"]] == ["b1"]


# ---------------------------------------------------------------------------
# The full unit set, which is what a batch run actually uses
# ---------------------------------------------------------------------------

def test_the_full_unit_set_always_contains_the_row_itself():
    row = {"unit_id": "s1", "soft_parents": ""}
    full = resolve_full_unit_set(row, "submissions_2026", {"submissions_2026": [row]})
    assert [r["unit_id"] for r in full["submissions_2026"]] == ["s1"]


def test_the_full_unit_set_spans_every_table_the_row_is_related_to():
    row = {"unit_id": "s1", "soft_parents": "nhs_organisations:n1"}
    tables = {
        "submissions_2026": [row],
        "nhs_organisations": [{"unit_id": "n1"}],
        "submissions_2025": [{"unit_id": "old1", "soft_parents": "submissions_2026:s1"}],
    }
    full = resolve_full_unit_set(row, "submissions_2026", tables)
    assert set(full) == {"submissions_2026", "nhs_organisations", "submissions_2025"}


def test_a_row_with_no_links_at_all_still_produces_a_usable_unit_set():
    """
    Most workfiles start here, so this must not be an empty dict: the
    reporting unit still has to resolve as Selected on its own charts.
    """
    row = {"unit_id": "s1", "soft_parents": ""}
    full = resolve_full_unit_set(row, "submissions_2026", {"submissions_2026": [row]})
    assert full == {"submissions_2026": [row]}


def test_the_full_unit_set_keeps_both_rows_when_one_table_holds_two():
    """
    Stated in the docstring as explicitly not to be collapsed. Losing one
    here would drop a submission out of "Selected" on every chart.
    """
    row = {"unit_id": "n1", "soft_parents": ""}
    tables = {
        "nhs_organisations": [row],
        "submissions_2026": [
            {"unit_id": "s1", "soft_parents": "nhs_organisations:n1"},
            {"unit_id": "s2", "soft_parents": "nhs_organisations:n1"},
        ],
    }
    full = resolve_full_unit_set(row, "nhs_organisations", tables)
    assert [r["unit_id"] for r in full["submissions_2026"]] == ["s1", "s2"]
