"""
population_layers.py
Builds an ordered list of population-filtered data shape copies from a
'^'-delimited populations string.

A filtered copy is still a data shape, distinguished only by its
population_label field. Every token produces a layer, including one that
resolves to no units.
"""

from dataclasses import replace

from chartgen.shared.normalisation_containers.shapes import (
    filter_shape, NumericSeries, NumericCompositional, CategoricalCompositional,
    TimeSeries,
)
from chartgen.shared.normalisation_containers.peer_group_tokens import (
    parse_peer_token, is_no_group_value,
)


def _get_shape_units(data_shape) -> list:
    """Return the flat list of units from any shape type."""
    if isinstance(data_shape, NumericSeries):
        return data_shape.units
    elif isinstance(data_shape, (NumericCompositional, CategoricalCompositional, TimeSeries)):
        return data_shape.metrics[0].units if data_shape.metrics else []
    return []


def build_population_layers(data_shape, populations_str: str,
                             units: list, selected_ids) -> list:
    """
    Build an ordered list of data shapes from a '^'-delimited populations
    string, each filtered to one population layer with population_label set.

    The first token is the scope, the full set being compared. Each later
    token is an independent subset of that scope. Tokens: 'All',
    'Selected', 'Name()' (the selected unit's own group), 'Name(Value)'
    (a named group). Returns [] only if populations_str is blank.

    Every non-blank token produces exactly one layer, in order, and is never
    dropped. An unresolvable token still produces a layer with an empty unit
    set. Whether the reporting unit has data for this chart must never be
    why a token disappears.

    Unit ids are compared as strings throughout.

    units and selected_ids must belong to the same table as data_shape's own
    population. The caller resolves that from data_shape.population_table.

    selected_ids is a set: 'Selected' can legitimately resolve to more than
    one unit, and both are highlighted.
    """
    if not populations_str or not populations_str.strip():
        return []

    shape_ids = {u.unit_id for u in _get_shape_units(data_shape)}

    unit_lookup = {r["unit_id"]: r for r in units}
    selected_ids = set(selected_ids) if selected_ids else set()
    # Name() empty-bracket resolution needs one representative id. With
    # more than one selected id, this picks one arbitrarily.
    representative_id = next(iter(selected_ids), None)

    def _resolve(token: str, scope_ids: set):
        """
        Resolve one token to (unit_ids, label) within scope_ids. Never
        returns None — an unresolvable token still returns an empty id set
        with its own best-available label (the raw token text, when no
        better label is available), so the token is never silently dropped
        by the caller.
        """
        if token == "All":
            return set(scope_ids), "All"

        if token == "Selected":
            ids = (selected_ids & set(scope_ids)) if selected_ids else set()
            return ids, "Selected"

        parsed = parse_peer_token(token)
        if parsed is not None:
            col, value = parsed
            if not value:  # Name() — selected unit's own group
                if not representative_id or representative_id not in unit_lookup:
                    return set(), token
                value = unit_lookup[representative_id].get(col, "")
                if is_no_group_value(value):
                    return set(), token
            ids = {
                r["unit_id"] for r in units
                if r.get(col) == value
                and r["unit_id"] in scope_ids
            }
            return ids, value

        # Unrecognised token: still produce an empty layer, never drop it.
        return set(), token

    results = []
    scope_ids = set(shape_ids)

    for i, token in enumerate(t.strip() for t in populations_str.split("^")):
        if not token:
            continue

        token_ids, label = _resolve(token, scope_ids)

        if i == 0:
            # The scope may resolve empty. Every later token then resolves
            # empty against it, rather than the layer list collapsing.
            scope_ids = token_ids

        filtered = filter_shape(data_shape, token_ids)
        filtered = replace(filtered, population_label=label)
        results.append(filtered)

    return results
