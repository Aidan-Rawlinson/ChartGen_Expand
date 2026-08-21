"""
population_layers.py
Builds an ordered list of population-filtered data shape copies from a
'^'-delimited populations string. Moved out of assembly_engine — this is
data-model logic (filtering a data shape into layers), not pptx logic.

A filtered copy is still a data shape, not a second kind of construct — it is
just one instance distinguished by its population_label field (see
Functional Spec §10.4 and Restructure_Plan.md "Key decisions").
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
    Build an ordered list of data shapes from a '^'-delimited populations string,
    each filtered to one population layer with population_label set. The first
    token defines the scope (the full set being compared); each subsequent token
    is an independent subset of that scope. Tokens: 'All' (every unit), 'Selected'
    (see below), 'Name()' (selected unit's own group), 'Name(Value)' (the named
    group). Returns [] only if populations_str itself is blank.

    Every non-blank token in populations_str always produces exactly one
    layer in the result, in order — never silently dropped. A token that
    can't be resolved (no selected unit, the selected unit's own group is
    blank/unset, the scope itself resolves to nothing) still produces a
    layer with an empty unit set, so the chart — and the Charts sheet's own
    summary-stats/units display — always shows what was actually passed in,
    not just whatever happened to have data. Whether the reporting unit
    itself has data for this particular chart must never be why a token
    disappears from the output altogether.

    Unit ids are compared as strings throughout.

    units and selected_ids must both belong to the same table as data_shape's
    own population — the caller (assembly_engine.insert_chart) resolves that
    table via data_shape.population_table before calling this.

    selected_ids is a set, not a single id: 'Selected' can legitimately
    resolve to more than one unit in this table (e.g. an organisation
    supporting two ICBs highlights both ICBs on an ICB-level chart) — this is
    intended behaviour, not a case to collapse to one.
    """
    if not populations_str or not populations_str.strip():
        return []

    shape_ids = {u.unit_id for u in _get_shape_units(data_shape)}

    unit_lookup = {r["unit_id"]: r for r in units}
    selected_ids = set(selected_ids) if selected_ids else set()
    # For Name() empty-bracket resolution ("selected unit's own group") a
    # single representative id is needed. With more than one selected id,
    # this picks one arbitrarily — a known simplification, worth revisiting
    # if it ever produces a wrong-looking group for a genuinely multi-parent
    # selection, but not a real case yet.
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

        # Unrecognised token shape — still produce an empty layer rather
        # than dropping it.
        return set(), token

    results = []
    scope_ids = set(shape_ids)

    for i, token in enumerate(t.strip() for t in populations_str.split("^")):
        if not token:
            continue

        token_ids, label = _resolve(token, scope_ids)

        if i == 0:
            # The scope itself may resolve empty (e.g. no selected unit at
            # all) — every subsequent token then also resolves empty
            # against it, correctly, rather than the whole chart losing its
            # population layers.
            scope_ids = token_ids

        filtered = filter_shape(data_shape, token_ids)
        filtered = replace(filtered, population_label=label)
        results.append(filtered)

    return results
