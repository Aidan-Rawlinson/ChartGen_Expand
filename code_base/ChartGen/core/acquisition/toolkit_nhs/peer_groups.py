"""
peer_groups.py
Peer-group menu-building — which Name()/Name(Value) populations-string tokens
to offer for a given unit table. Split out of local_config.py, where this was
misfiled as "shared infra" — it is peer-group domain logic. Uses the shared
column/token rule in shared.normalisation_containers.peer_group_tokens rather
than re-deriving it (population_layers.py is the other caller of that rule,
for resolving tokens rather than listing them).
"""

from core.shared.normalisation_containers.peer_group_tokens import (
    is_peer_group_column, is_no_group_value,
)


def get_peer_group_columns(units: list) -> list:
    """
    Return peer group column names (matching the Name() pattern) from the unit table, in column order.
    Does not include 'All' or 'Selected' — callers add those.
    """
    if not units:
        return []
    return [col for col in units[0].keys() if is_peer_group_column(col)]


def get_peer_group_value_options(units: list) -> list:
    """
    Return populations-string tokens for every peer group column, in column order.
    For each Name() column, yields the bare token first, then one Name(Value) token
    per distinct value present in that column, sorted alphabetically, excluding
    blank and 'x' (both mean the unit has no group for that column).
    Does not include 'All' or 'Selected' — callers add those.
    """
    if not units:
        return []
    options = []
    for col in get_peer_group_columns(units):
        name = col[:-2]  # strip trailing "()"
        options.append(col)
        values = sorted({
            (r.get(col) or "").strip() for r in units
            if not is_no_group_value(r.get(col))
        })
        options.extend(f"{name}({v})" for v in values)
    return options
