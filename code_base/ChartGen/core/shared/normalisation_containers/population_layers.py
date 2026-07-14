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

from core.shared.normalisation_containers.shapes import (
    filter_shape, NumericSeries, NumericCompositional, CategoricalCompositional,
)
from core.shared.normalisation_containers.peer_group_tokens import (
    parse_peer_token, is_no_group_value,
)


def _get_shape_units(data_shape) -> list:
    """Return the flat list of units from any shape type."""
    if isinstance(data_shape, NumericSeries):
        return data_shape.units
    elif isinstance(data_shape, (NumericCompositional, CategoricalCompositional)):
        return data_shape.metrics[0].units if data_shape.metrics else []
    return []


def build_population_layers(data_shape, populations_str: str,
                             units: list, report_context) -> list:
    """
    Build an ordered list of data shapes from a '^'-delimited populations string,
    each filtered to one population layer with population_label set. The first
    token defines the scope (the full set being compared); each subsequent token
    is an independent subset of that scope. Tokens: 'All' (every unit), 'Selected'
    (current organisation), 'Name()' (selected unit's own group), 'Name(Value)'
    (the named group). Returns [] if populations_str is blank or the scope
    resolves empty. Unit ids are compared as strings throughout.
    """
    if not populations_str or not populations_str.strip():
        return []

    shape_ids = {u.unit_id for u in _get_shape_units(data_shape)}
    if not shape_ids:
        return []

    unit_lookup = {r["unit_id"]: r for r in units}
    selected_id = report_context.unit_id if report_context else None
    selected_org_id = report_context.organisation_id if report_context else None

    def _resolve(token: str, scope_ids: set):
        """Resolve one token to (unit_ids, label) within scope_ids, or None."""
        if token == "All":
            return set(scope_ids), "All"

        if token == "Selected":
            if not selected_org_id:
                return None
            ids = {
                r["unit_id"] for r in units
                if r["organisation_id"] == selected_org_id
                and r["unit_id"] in scope_ids
            }
            return ids, "Selected"

        parsed = parse_peer_token(token)
        if parsed is not None:
            col, value = parsed
            if not value:  # Name() — selected unit's own group
                if not selected_id or selected_id not in unit_lookup:
                    return None
                value = unit_lookup[selected_id].get(col, "")
                if is_no_group_value(value):
                    return None
            ids = {
                r["unit_id"] for r in units
                if r.get(col) == value
                and r["unit_id"] in scope_ids
            }
            return ids, value

        return None

    results = []
    scope_ids = set(shape_ids)

    for i, token in enumerate(t.strip() for t in populations_str.split("^")):
        if not token:
            continue

        resolved = _resolve(token, scope_ids)
        if resolved is None:
            if i == 0:
                return []
            continue
        token_ids, label = resolved

        if i == 0:
            if not token_ids:
                return []
            scope_ids = token_ids

        filtered = filter_shape(data_shape, token_ids)
        filtered = replace(filtered, population_label=label)
        results.append(filtered)

    return results
