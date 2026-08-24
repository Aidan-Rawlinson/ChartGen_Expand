"""
Tests for shared/infrastructure/id_generation.py

Ids are described as "short, permanent, never-reused". Reuse is the failure
that matters: a reissued id silently rebinds something else's reference,
so a Stat Tag or a Chart Store entry starts resolving to the wrong data
with nothing raising.

shared/infrastructure/CLAUDE.md: "Counters are never recomputed from
surviving rows." That is what makes ids permanent rather than merely
unique, and it is the kind of thing that looks like dead weight to a later
reader and gets "tidied up".
"""

from chartgen.shared.infrastructure.id_generation import (
    from_base36,
    next_id,
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


def test_encoding_then_decoding_returns_the_original_number():
    for n in [0, 1, 9, 10, 35, 36, 37, 1295, 1296, 99999]:
        assert from_base36(to_base36(n)) == n


def test_decoding_is_case_insensitive():
    """
    An id typed by hand into a spreadsheet cell may come back capitalised,
    and it still has to resolve to the same number.
    """
    assert from_base36("Z") == from_base36("z")
    assert from_base36("1A") == from_base36("1a")


# ---------------------------------------------------------------------------
# Issuing ids from the persisted counter
# ---------------------------------------------------------------------------

def test_the_first_id_from_an_empty_counter_is_one_not_zero():
    """
    Starting at 1 means no id is ever the string "0", which would be
    indistinguishable from an empty cell in a CSV or a spreadsheet.
    """
    settings = {}
    assert next_id(settings, "next_thing_id") == "1"


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
    settings = {"next_thing_id": "35"}
    assert next_id(settings, "next_thing_id") == "10"   # 36 in base 36


def test_a_blank_counter_value_is_treated_as_not_yet_started():
    """A CSV round-trip can turn an absent value into an empty string."""
    assert next_id({"next_thing_id": ""}, "next_thing_id") == "1"


def test_deleting_rows_does_not_hand_their_ids_back_out():
    """
    The "never recomputed from surviving rows" rule, stated as behaviour.
    The counter knows nothing about what still exists, which is precisely
    why a deleted row's id can never be reissued to something new.
    """
    settings = {}
    first = next_id(settings, "next_thing_id")
    second = next_id(settings, "next_thing_id")

    # The caller deletes everything it just created. The counter is untouched.
    surviving_rows = []
    assert surviving_rows == []

    third = next_id(settings, "next_thing_id")
    assert third not in (first, second)
    assert third == "3"
