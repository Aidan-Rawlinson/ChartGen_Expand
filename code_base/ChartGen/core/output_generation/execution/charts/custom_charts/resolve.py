"""
resolve.py
Resolves a chart_type_ref to a callable (built-in first, custom second),
and merges a workfile's saved custom charts into the built-in chart-type
listings wherever those are shown to the user — the Charts sheet's
Visualisation dropdown, the Running Order row-edit dialog, and the
Running Order .xlsx per-row dropdown.

Deliberately not used by generation.py's auto-default-on-fetch behaviour
(backfill_default_chart_types) — auto-defaulting a fresh Running Order row
to a user's own custom chart the moment its shape becomes known would be
presumptuous and order-dependent in a way today's built-in-only default
isn't. That path continues to read only chart_type_map.py's static config,
unchanged.
"""

from core.output_generation.execution.charts.base_charts import CHART_REGISTRY
from core.output_generation.execution.charts.custom_charts.gate import (
    compile_custom_chart, CustomChartError,
)


def get_chart_callable(chart_type_ref: str, custom_chart_code: dict):
    """
    Resolve a chart_type_ref to a callable — built-in registry first, then
    the workfile's own saved custom charts. Raises ValueError if neither
    has it (matching registry.render_chart's existing error for an unknown
    ref). Raises CustomChartError if a custom chart's stored source no
    longer compiles (should not happen for anything that passed the gate
    at save time, but a workfile can be hand-edited outside the app).
    """
    if chart_type_ref in CHART_REGISTRY:
        return CHART_REGISTRY[chart_type_ref]
    if custom_chart_code and chart_type_ref in custom_chart_code:
        return compile_custom_chart(custom_chart_code[chart_type_ref])
    raise ValueError(f"Unknown chart_type_ref: {chart_type_ref}")


def merge_custom_refs_for_shape(shape_type: str, built_in_refs: list, custom_chart_rows: list) -> list:
    """
    Append this workfile's saved custom chart_type_refs matching shape_type
    to a built-in refs list, for a dropdown/listing site. Returns
    built_in_refs unchanged if custom_chart_rows is empty/None.
    """
    if not custom_chart_rows:
        return built_in_refs
    custom_refs = [
        r["chart_type_ref"] for r in custom_chart_rows
        if r.get("shape_type") == shape_type
    ]
    return built_in_refs + custom_refs


def custom_chart_descriptions(shape_type: str, custom_chart_rows: list) -> list:
    """
    Return (chart_type_ref, description) pairs for this workfile's saved
    custom charts matching shape_type, in the same shape get_valid_chart_types
    returns for built-ins — for merging into a dropdown's description map.
    """
    if not custom_chart_rows:
        return []
    pairs = []
    for r in custom_chart_rows:
        if r.get("shape_type") != shape_type:
            continue
        notes = str(r.get("notes", "") or "").strip()
        desc = f"Custom: {r['chart_type_ref']} — {notes}" if notes else f"Custom: {r['chart_type_ref']}"
        pairs.append((r["chart_type_ref"], desc))
    return pairs
