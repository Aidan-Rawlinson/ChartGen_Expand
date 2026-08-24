"""
Tests for shared/infrastructure/id_generation.py

Ids are described as "short, permanent, never-reused". Reuse is the failure
that matters: a reissued id silently rebinds something else's reference, so a
Stat Tag or a Chart Store entry starts resolving to the wrong data with
nothing raising.

The subtlety these protect is that **an id can arrive from the user as well
as from the system**. Every id space has an Excel round trip, and a person
editing that spreadsheet may number things however suits them -- "AB1, AB2,
AB3" then "AC1, AC2, AC3" is a natural way to build tabular material. So the
counter cannot be assumed to know about every id in use.

next_unique_id therefore checks rather than infers. An earlier version
decoded each id in use as base-36 and pushed the counter past the highest,
which had two problems worth keeping fixed: an id it could not decode was
silently ignored, and a decoded value like "AC3" (13,395) got written into
the counter, so every later id became a long string derived from someone
else's naming scheme.

shared/infrastructure/CLAUDE.md: "Counters are never recomputed from
surviving rows." That is what makes ids permanent rather than merely unique,
and it is the kind of thing that looks like dead weight to a later reader.
"""

import pytest

from chartgen.shared.infrastructure.id_generation import (
    next_id,
    next_unique_id,
    to_base36,
)


# ---------------------------------------------------------------------------
# The digit encoding
# ---------------------------------------------------------------------------

def test_base36_rolls_over_into_letters_after_nine():
    assert to_base36(9) == "9"
    assert to_base36(10) == "a"
    assert to_base36(35) == "z"


def test_base36_carries_into_a_second_digit_at_thirty_six():
    assert to_base36(36) == "10"


def test_zero_encodes_as_a_single_zero():
    assert to_base36(0) == "0"


# ---------------------------------------------------------------------------
# next_id: the bare counter, with no uniqueness check
# ---------------------------------------------------------------------------

def test_the_first_id_from_an_empty_counter_is_one_not_zero():
    """
    Starting at 1 means no id is ever the string "0", which would be
    indistinguishable from an empty cell in a CSV or a spreadsheet.
    """
    assert next_id({}, "next_thing_id") == "1"


def test_each_call_issues_a_different_id():
    settings = {}
    issued = [next_id(settings, "next_thing_id") for _ in range(5)]
    assert issued == ["1", "2", "3", "4", "5"]
    assert len(set(issued)) == 5


def test_the_counter_is_written_back_into_settings():
    """
    The counter has to survive into the saved workfile, or the next session
    starts from scratch and reissues ids already in use.
    """
    settings = {}
    next_id(settings, "next_thing_id")
    next_id(settings, "next_thing_id")
    assert settings["next_thing_id"] == "2"


def test_each_id_space_counts_independently():
    """
    Separate counter keys must never interleave: a Stat Tag and an Output
    Table can both legitimately be id "3".
    """
    settings = {}
    assert next_id(settings, "next_stat_tag") == "1"
    assert next_id(settings, "next_table_id") == "1"
    assert next_id(settings, "next_stat_tag") == "2"


def test_issuing_resumes_from_a_counter_restored_from_a_saved_workfile():
    assert next_id({"next_thing_id": "35"}, "next_thing_id") == "10"   # 36 in base 36


def test_a_blank_counter_value_is_treated_as_not_yet_started():
    """A CSV round-trip can turn an absent value into an empty string."""
    assert next_id({"next_thing_id": ""}, "next_thing_id") == "1"


# ---------------------------------------------------------------------------
# next_unique_id: the guarantee
# ---------------------------------------------------------------------------

def test_an_id_already_in_use_is_never_issued():
    """
    The counter is at zero and would otherwise hand out "1", which is
    taken. It skips to the first free value instead.
    """
    assert next_unique_id({}, "k", "", {"1", "2"}) == "3"


def test_the_prefix_is_applied_before_the_uniqueness_check():
    """
    "T1" being in use must block "T1", not "1". Checking the bare counter
    value would let a prefixed duplicate straight through.
    """
    assert next_unique_id({}, "k", "T", {"T1", "T2"}) == "T3"


def test_a_prefixed_space_is_not_blocked_by_the_unprefixed_value():
    """The other half: "1" in use says nothing about "T1"."""
    assert next_unique_id({}, "k", "T", {"1", "2", "3"}) == "T1"


def test_nothing_in_use_means_the_counter_is_followed_directly():
    assert next_unique_id({}, "k", "C", set()) == "C1"


def test_an_id_differing_only_in_case_counts_as_in_use():
    """
    A Stat Tag is matched in a template by its exact literal text, so
    "[ab1]" and "[AB1]" are different tokens. Issuing one alongside the
    other would give two ids a person reads as one, and a template author
    no way to tell which they had referenced.
    """
    issued = next_unique_id({}, "k", "", {"AB1"})
    assert issued.casefold() != "ab1"


def test_a_hand_typed_id_that_is_not_base_36_at_all_still_blocks_its_value():
    """
    The bug this design removes. An approach that decoded ids to find the
    highest had to ignore anything it could not parse, so a user's own id
    played no part in the decision. Here nothing is parsed, so "1" being
    taken is honoured however it got there.
    """
    assert next_unique_id({}, "k", "", {"1", "AB-1", "Table 2"}) == "2"


def test_surrounding_whitespace_on_an_id_in_use_is_ignored():
    """A spreadsheet cell very often arrives with a stray space."""
    assert next_unique_id({}, "k", "", {" 1 "}) == "2"


def test_a_blank_entry_among_the_ids_in_use_blocks_nothing():
    """
    A row with no id yet is exactly what is about to be given one, so it
    must not block the first candidate.
    """
    assert next_unique_id({}, "k", "", {"", None}) == "1"


def test_aidan_s_case_a_user_numbering_tables_ab1_ab2_then_ac1_ac2():
    """
    The scenario that prompted this change. Numbering tabular material
    "AB1, AB2, AB3" then "AC1, AC2, AC3" is a natural thing to do in the
    Excel round trip.

    Two things must hold. The issued id must not duplicate any of them.
    And it must stay short: the previous implementation decoded "AC3" as
    base-36 to 13,395 and wrote that into the counter, so every later id
    became a three-character string derived from the user's naming scheme,
    against a module whose stated aim is ids short enough to sit in a
    PowerPoint table cell.
    """
    in_use = {"AB1", "AB2", "AB3", "AC1", "AC2", "AC3"}
    settings = {}

    issued = next_unique_id(settings, "next_table_id", "", in_use)

    assert issued.casefold() not in {i.casefold() for i in in_use}
    assert len(issued) <= 2
    assert issued == "1"


def test_several_ids_issued_in_a_row_do_not_collide_with_each_other():
    """
    The caller adds each new id to the set as it goes, which is how two
    blank rows in one spreadsheet upload stay distinct.
    """
    settings = {}
    in_use = {"1", "2"}
    issued = []
    for _ in range(3):
        new = next_unique_id(settings, "k", "", in_use)
        issued.append(new)
        in_use.add(new)

    assert issued == ["3", "4", "5"]
    assert len(set(issued)) == 3


def test_the_counter_advances_past_candidates_that_were_taken():
    """
    A rejected candidate still consumes its counter value, so the work of
    skipping is done once rather than repeated on every later call.
    """
    settings = {}
    next_unique_id(settings, "k", "", {"1", "2", "3"})
    assert settings["k"] == "4"


def test_the_counter_is_not_set_from_the_ids_in_use():
    """
    "Counters are never recomputed from surviving rows." The counter
    advances one at a time until a candidate is free; it is never assigned
    a value read off the rows. The previous implementation broke this rule,
    and shared/infrastructure/CLAUDE.md contradicted itself as a result.
    """
    settings = {}
    next_unique_id(settings, "k", "", {"zzzzz"})
    assert settings["k"] == "1"


def test_a_deleted_row_s_id_is_not_handed_back_out():
    """
    The counter knows nothing about what still exists, which is precisely
    why a deleted row's id can never be reissued to something new.
    """
    settings = {}
    first = next_unique_id(settings, "k", "", set())
    second = next_unique_id(settings, "k", "", {first})

    # Both rows are now deleted. The counter is untouched by that.
    third = next_unique_id(settings, "k", "", set())

    assert third not in (first, second)


def test_the_ids_in_use_argument_is_required():
    """
    Deliberately has no default. A caller that cannot say what is in use
    cannot be given a guaranteed-unique id, and should fail here rather
    than silently skip the check -- which is what an optional argument
    invited.
    """
    with pytest.raises(TypeError):
        next_unique_id({}, "k", "")
