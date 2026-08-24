"""
Tests for shared/normalisation_containers/peer_group_tokens.py

The "Name()" convention is how a population string names a peer group. It is
shared between peer_groups.py, which decides which tokens to offer in the
dropdown, and population_layers.py, which resolves which units a token
matches. If the two ever read the convention differently, the dropdown
offers a group that resolves to nobody, and the chart shows an empty layer
with no explanation.

The rule most worth pinning is that a blank value and the literal "x" both
mean "no group" and are "treated identically". That is a data-entry
convention from the population tables, and a unit marked "x" must not be
gathered into a group named "x".
"""

from chartgen.shared.normalisation_containers.peer_group_tokens import (
    is_no_group_value,
    is_peer_group_column,
    parse_peer_token,
)


# ---------------------------------------------------------------------------
# Recognising a peer-group column
# ---------------------------------------------------------------------------

def test_a_column_ending_in_brackets_is_a_peer_group_column():
    assert is_peer_group_column("Region()") is True


def test_an_ordinary_column_is_not_a_peer_group_column():
    for column in ["unit_id", "unit_code", "unit_name", "soft_parents", "Beds"]:
        assert is_peer_group_column(column) is False


def test_a_column_with_brackets_in_the_middle_is_not_a_peer_group_column():
    """The suffix is the signal, not the presence of brackets anywhere."""
    assert is_peer_group_column("Region() notes") is False


# ---------------------------------------------------------------------------
# "No group": blank and "x" mean the same thing
# ---------------------------------------------------------------------------

def test_a_blank_value_means_no_group():
    assert is_no_group_value("") is True


def test_the_literal_x_means_no_group():
    """
    The data-entry convention. A unit marked "x" is excluded, not put in a
    group called "x".
    """
    assert is_no_group_value("x") is True


def test_a_missing_value_means_no_group():
    assert is_no_group_value(None) is True


def test_whitespace_only_means_no_group():
    assert is_no_group_value("   ") is True


def test_a_real_group_name_is_not_no_group():
    for value in ["North", "Teaching", "Small acute"]:
        assert is_no_group_value(value) is False


def test_the_no_group_check_is_case_sensitive_for_x():
    """
    Recording current behaviour, not endorsing it: "X" is treated as a real
    group name rather than as "no group". Worth knowing if a population
    table ever comes back from Excel with capitalised cells.
    """
    assert is_no_group_value("X") is False


# ---------------------------------------------------------------------------
# Parsing a populations-string token
# ---------------------------------------------------------------------------

def test_an_empty_bracket_token_means_the_selected_unit_s_own_group():
    """
    "Region()" means "whichever region the reporting unit is in", resolved
    per unit at run time rather than named up front.
    """
    assert parse_peer_token("Region()") == ("Region()", "")


def test_a_filled_bracket_token_names_an_explicit_group():
    assert parse_peer_token("Region(North)") == ("Region()", "North")


def test_the_column_name_comes_back_in_its_own_column_form():
    """
    The second element is the value; the first is always the column as it
    appears in the population table, brackets included, ready to look up.
    """
    column, value = parse_peer_token("Region(North)")
    assert column == "Region()"
    assert is_peer_group_column(column) is True


def test_the_non_peer_group_tokens_are_not_peer_tokens():
    """
    "All" and "Selected" are the two scope tokens. Returning None is how
    population_layers tells them apart from a peer group.
    """
    assert parse_peer_token("All") is None
    assert parse_peer_token("Selected") is None


def test_a_group_value_containing_a_space_is_preserved():
    assert parse_peer_token("Type(Small acute)") == ("Type()", "Small acute")


def test_a_group_value_containing_brackets_is_split_on_the_first_bracket():
    """
    Recording current behaviour: the split is on the first "(", so a value
    with its own brackets keeps them.
    """
    assert parse_peer_token("Type(Acute (small))") == ("Type()", "Acute (small)")
