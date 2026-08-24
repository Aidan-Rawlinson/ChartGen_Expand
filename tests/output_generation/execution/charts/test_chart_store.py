"""
Tests for output_generation/execution/charts/chart_store.py

A Chart Store id is referenced from an Output Table cell as "{Cn}". If an id
were ever reissued to a different entry, that marker becomes ambiguous and
the table renders someone else's chart, with nothing raising.

Ids also arrive from outside the system, through the Excel round trip in
chart_store_xlsx.py, in whatever form the person typed. So uniqueness is
checked against the ids actually in use rather than inferred from the
counter.
"""

import pytest

from chartgen.output_generation.execution.charts.chart_store import (
    chart_store_row_label,
    next_chart_store_id,
)


# ---------------------------------------------------------------------------
# next_chart_store_id
# ---------------------------------------------------------------------------

def test_an_id_carries_the_c_prefix():
    """
    The "C" disambiguates a Chart Store id from a Stat Tag ("T") where both
    appear in the same Output Table cell grammar.
    """
    assert next_chart_store_id({}, set()).startswith("C")


def test_the_first_id_in_a_fresh_workfile_is_short():
    assert next_chart_store_id({}, set()) == "C1"


def test_an_id_already_on_a_row_is_never_reissued():
    ids_in_use = {"C1", "C2", "C3"}
    assert next_chart_store_id({}, ids_in_use) not in ids_in_use


def test_a_hand_typed_id_from_excel_is_respected():
    """
    "AB1" is not a value the counter would ever produce, and an
    implementation that decoded ids to find the highest would ignore it
    entirely. It still has to block that id.
    """
    ids_in_use = {"AB1", "AB2", "C1"}
    issued = next_chart_store_id({}, ids_in_use)
    assert issued.casefold() not in {i.casefold() for i in ids_in_use}


def test_ids_stay_short_after_a_user_numbers_rows_their_own_way():
    """
    Aidan's case, on this id space. The old implementation decoded "AC3" to
    13,395 and wrote it into the counter, so every later id became a long
    string derived from the user's own scheme.
    """
    ids_in_use = {"CAB1", "CAB2", "CAB3", "CAC1", "CAC2", "CAC3"}
    issued = next_chart_store_id({}, ids_in_use)
    assert len(issued) <= 3
    assert issued.casefold() not in {i.casefold() for i in ids_in_use}


def test_successive_ids_differ_when_the_caller_tracks_what_it_has_issued():
    """
    How assign_missing_chart_store_ids keeps two blank rows in one upload
    distinct.
    """
    settings = {}
    ids_in_use = set()
    issued = []
    for _ in range(3):
        new = next_chart_store_id(settings, ids_in_use)
        ids_in_use.add(new)
        issued.append(new)

    assert issued == ["C1", "C2", "C3"]


def test_the_counter_persists_into_settings():
    settings = {}
    next_chart_store_id(settings, set())
    assert settings["next_chart_store_id"] == "1"


def test_the_chart_store_space_has_its_own_counter():
    settings = {}
    next_chart_store_id(settings, set())
    assert "next_chart_store_id" in settings
    assert "next_stat_tag_id" not in settings


def test_the_ids_in_use_argument_is_required():
    with pytest.raises(TypeError):
        next_chart_store_id({})


# ---------------------------------------------------------------------------
# chart_store_row_label
# ---------------------------------------------------------------------------

def test_a_row_label_names_the_id_the_chart_type_and_the_data():
    """
    What the Charts sheet's Chart Store dropdown shows, so a person can
    tell two saved charts apart.
    """
    row = {"chart_store_id": "C1", "base_chart_name": "dot_strip", "cache_file": "aa.json"}
    label = chart_store_row_label(row, {"aa.json": "Chart_0001  —  Beds per 100k"})

    assert "C1" in label
    assert "dot_strip" in label
    assert "Beds per 100k" in label


def test_a_row_label_falls_back_to_the_filename_when_no_label_is_known():
    """
    A cache file deleted since the entry was saved must not make the
    dropdown unreadable or raise.
    """
    row = {"chart_store_id": "C1", "base_chart_name": "dot_strip", "cache_file": "aa.json"}
    assert "aa.json" in chart_store_row_label(row, {})
