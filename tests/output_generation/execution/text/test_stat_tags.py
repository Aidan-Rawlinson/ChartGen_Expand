"""
Tests for output_generation/execution/text/stat_tags.py

A Stat Tag is the literal text a person types into a PowerPoint template or
an Output Table cell, and `update_text` swaps it for a figure at generation
time. So the tag is a reference someone has written down somewhere the
system cannot see. If a tag is ever reissued to a different row, every
template already using it silently starts printing a different number, and
nothing raises.

Tags also arrive from outside the system, through the Excel round trip in
stat_tags_xlsx.py, in whatever form the person typed. Uniqueness therefore
cannot be inferred from the counter, and next_stat_tag does not try: it
checks the candidate against the tags actually in use.
"""

import pytest

from chartgen.output_generation.execution.text.stat_tags import (
    layer_display_label,
    next_stat_tag,
)


# ---------------------------------------------------------------------------
# next_stat_tag
# ---------------------------------------------------------------------------

def test_a_tag_carries_the_t_prefix():
    """
    The "T" disambiguates a Stat Tag from a Chart Store id ("C") where both
    appear in the same Output Table cell grammar.
    """
    assert next_stat_tag({}, set()).startswith("T")


def test_the_first_tag_in_a_fresh_workfile_is_short():
    assert next_stat_tag({}, set()) == "T1"


def test_a_tag_already_on_a_row_is_never_reissued():
    tags_in_use = {"T1", "T2", "T3"}
    assert next_stat_tag({}, tags_in_use) not in tags_in_use


def test_a_hand_typed_tag_from_excel_is_respected():
    """
    "AB1" is not a value the counter would ever produce, and an
    implementation that decoded tags to find the highest would ignore it
    entirely. It still has to block that tag.
    """
    tags_in_use = {"AB1", "AB2", "T1"}
    issued = next_stat_tag({}, tags_in_use)
    assert issued.casefold() not in {t.casefold() for t in tags_in_use}


def test_a_tag_typed_with_punctuation_is_respected():
    """
    "T-1" cannot be decoded as a counter value at all. Nothing here decodes
    anything, so it blocks its own text and nothing more.
    """
    assert next_stat_tag({}, {"T-1"}) == "T1"


def test_tags_stay_short_after_a_user_numbers_rows_their_own_way():
    """
    Aidan's case. The old implementation decoded "AC3" to 13,395 and wrote
    it into the counter, so every later tag became a long string derived
    from the user's scheme. A tag too wide for its cell changes an Output
    Table's size.
    """
    tags_in_use = {"TAB1", "TAB2", "TAB3", "TAC1", "TAC2", "TAC3"}
    issued = next_stat_tag({}, tags_in_use)
    assert len(issued) <= 3
    assert issued.casefold() not in {t.casefold() for t in tags_in_use}


def test_successive_tags_differ_when_the_caller_tracks_what_it_has_issued():
    """
    How the Text tab adds several tags in one click, and how
    assign_missing_tags handles two blank rows in one upload.
    """
    settings = {}
    tags_in_use = set()
    issued = []
    for _ in range(3):
        tag = next_stat_tag(settings, tags_in_use)
        tags_in_use.add(tag)
        issued.append(tag)

    assert issued == ["T1", "T2", "T3"]


def test_the_counter_persists_into_settings():
    """
    So the next session resumes rather than starting again and reissuing
    tags already in templates.
    """
    settings = {}
    next_stat_tag(settings, set())
    assert settings["next_stat_tag_id"] == "1"


def test_the_tag_space_has_its_own_counter():
    """
    Shared encoding, separate counters. A Stat Tag and an Output Table can
    both legitimately be numbered 1.
    """
    settings = {}
    next_stat_tag(settings, set())
    assert "next_stat_tag_id" in settings
    assert "next_table_id" not in settings


def test_the_tags_in_use_argument_is_required():
    """
    A caller that cannot say which tags exist cannot be given a safe tag.
    """
    with pytest.raises(TypeError):
        next_stat_tag({})


# ---------------------------------------------------------------------------
# layer_display_label
# ---------------------------------------------------------------------------

def test_a_static_token_is_shown_as_its_own_text():
    """
    "Region(North)" already says which group it means, so the resolved
    label would add nothing.
    """
    assert layer_display_label("Region(North)", "North") == "Region(North)"
    assert layer_display_label("All", "All") == "All"
    assert layer_display_label("Selected", "Selected") == "Selected"


def test_an_empty_bracket_token_shows_both_the_token_and_what_it_resolved_to():
    """
    The documented distinction, and the reason this function exists.
    "Region()" tracks whoever is currently selected, so showing only
    "South East" would make it look like a fixed reference to that region
    when it will mean something different for the next organisation.
    """
    assert layer_display_label("Region()", "South East") == "Region() — South East"


def test_a_blank_token_falls_back_to_the_resolved_label():
    assert layer_display_label("", "All") == "All"
