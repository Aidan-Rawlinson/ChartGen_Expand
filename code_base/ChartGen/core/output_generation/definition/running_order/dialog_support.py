"""
dialog_support.py
Row-edit dialog support: filtering chart-type options to those valid for a
row's data shape, and building/parsing the populations string in its fixed
canonical order (All -> peer groups -> Selected). Used by the Running Order
tab's row-edit dialog; kept here because both rules are about the Running
Order's own schema and validity, not about rendering.
"""

from core.output_generation.execution.charts.chart_type_map import get_chart_types_by_shape
from core.output_generation.execution.charts.custom_charts import merge_custom_refs_for_shape
# Re-exported for existing callers — the logic itself now lives in
# core.shared.infrastructure.period_ids, since shared-layer normalisation
# code (cut_resolution.py) needs it too and can't import from
# output_generation.definition (Architecture, Section 2).
from core.shared.infrastructure.period_ids import (  # noqa: F401
    parse_metric_periods_string, build_metric_periods_string,
)


def get_valid_chart_refs_for_cache_file(cache_file: str, manifest: dict, converts_to_metrics: bool = False,
                                        custom_chart_rows: list = None) -> list:
    """
    Return the list of base_chart_name values valid for the data shape of the
    given cache file, per the shape/chart-type pairing in chart_type_map.csv,
    plus this workfile's own saved custom charts for that same shape
    (custom_chart_rows — omit or pass None/[] to list built-ins only, e.g.
    for the auto-default-on-fetch path in generation.py, which deliberately
    never defaults to a custom chart). Falls back to every chart type
    across all shapes if the cache file or its shape type is not found in
    the manifest.

    converts_to_metrics: True when the row's metric_periods is set, meaning
    a TimeSeries cache_file is converted to a NumericSeries snapshot before
    rendering (shape_transforms.maybe_convert_periods_to_metrics) — so valid
    chart types are NumericSeries's, not TimeSeries's, for that row only.
    """
    shape_type = (manifest.get(cache_file) or {}).get("shape_type", "")
    if converts_to_metrics and shape_type == "TimeSeries":
        shape_type = "NumericSeries"
    chart_type_by_shape = get_chart_types_by_shape()
    valid_refs = chart_type_by_shape.get(shape_type, [])
    if not valid_refs:
        valid_refs = [ref for refs in chart_type_by_shape.values() for ref in refs]
    return merge_custom_refs_for_shape(shape_type, valid_refs, custom_chart_rows)



def build_populations_options(peer_options: list) -> list:
    """Return the full ordered list of selectable populations-string tokens: All, then peer options, then Selected."""
    return ["All"] + list(peer_options) + ["Selected"]


def parse_populations_string(populations_str: str, valid_options: list) -> list:
    """Parse a '^'-delimited populations string into a list of tokens, dropping any not in valid_options."""
    if not populations_str:
        return []
    return [p.strip() for p in populations_str.split("^") if p.strip() and p.strip() in valid_options]


def build_populations_string(selected_tokens: list, valid_options: list) -> str:
    """
    Build a '^'-delimited populations string from a set of selected tokens,
    in the fixed canonical order (All -> peer groups -> Selected) rather than
    whatever order the tokens were selected in.
    """
    selected_set = set(selected_tokens)
    return "^".join(p for p in valid_options if p in selected_set)
