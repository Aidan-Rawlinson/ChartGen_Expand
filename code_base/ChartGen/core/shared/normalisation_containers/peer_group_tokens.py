"""
peer_group_tokens.py
Shared rule for the Name()/Name(Value) peer-group token convention used across
Running Order populations strings and unit table columns: a column name plus
"()" is a peer-group token; the bracket may be empty (the selected unit's own
group) or hold a value (an explicit named group). A blank value or the literal
"x" both mean "no group" and are treated identically.

Used by peer_groups.py (menu-building — which tokens to offer) and
population_layers.py (resolving — which units a given token actually matches),
so both apply the same rule instead of each re-deriving it.
"""

NO_GROUP_VALUES = {"", "x"}


def is_peer_group_column(col: str) -> bool:
    """Return True if a unit-table column name is a peer-group column (ends in '()')."""
    return col.endswith("()")


def is_no_group_value(value) -> bool:
    """Return True if a peer-group column's value for a unit means 'no group' (blank or 'x')."""
    return (value or "").strip() in NO_GROUP_VALUES


def parse_peer_token(token: str):
    """
    Parse a populations-string token of the form 'Name()' or 'Name(Value)'.

    Returns (column, value) where column is 'Name()' and value is '' (own-group
    form) or 'Value' (explicit-group form), or None if the token is not a
    peer-group token at all (e.g. 'All', 'Selected').
    """
    if not (token.endswith(")") and "(" in token):
        return None
    col_name, value = token[:-1].split("(", 1)
    return col_name + "()", value
