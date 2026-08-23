"""
cut_resolution.py
Composes the shared middle of one chart's own cut of an already-loaded data
shape: period-range trim, then metric-periods conversion, then
population-table, target-rows and selected-ids resolution.

Two things are deliberately left to the caller. build_population_layers,
because the Charts sheet needs target_rows for its populations widget
before it knows which populations string to resolve. And loading the shape
from the cache, because that differs per caller.

Raises rather than swallowing, so each caller keeps its own error handling.
Callers today are insert_chart, the Charts sheet, Stat Tags, the Chart
Store and Output Tables.
"""

from chartgen.shared.infrastructure.period_ids import parse_metric_periods_string, extract_period_id, extract_metric_period_ids
from chartgen.shared.normalisation_containers.shapes import apply_period_range
from chartgen.shared.normalisation_containers.shape_transforms import maybe_convert_periods_to_metrics


def prepare_chart_cut(
    data_shape, shape_type: str,
    start_period: str, end_period: str, metric_periods_str: str,
    tables: dict, table_order: list, full_unit_set: dict,
):
    """
    Apply one chart's period-range trim and metric-periods conversion to an
    already-loaded data shape, then resolve which population table its units
    belong to and which ids are "Selected" for the current reporting unit.
    Everything build_population_layers needs except the populations string.

    start_period, end_period and metric_periods_str arrive exactly as stored
    on a Running Order row, Chart Store entry or Stat Tag: typically
    "period_label(period_id)", or a bare id typed by hand. The bare id is
    extracted here and only here, so callers pass their stored value through
    unmodified and the stored string is never rewritten.

    The range trim runs before the metric-periods conversion, so an id the
    trim has already cut out surfaces as not found rather than silently
    succeeding against the untrimmed shape.

    The population table is read off data_shape.population_table, falling
    back to table_order[0] only for cached data predating that field.

    Returns (cut_shape, effective_shape_type, target_rows, selected_ids).
      - cut_shape is data_shape after both steps. A caller building its own
        "no populations resolved" fallback should use this, not the original,
        so the fallback reflects the same trims.
      - effective_shape_type is "NumericSeries" once a metric_periods
        conversion has applied, otherwise shape_type unchanged.
      - target_rows and selected_ids are build_population_layers'
        own units and selected_ids parameters.

    Does not raise for a metric_periods id absent from the trimmed shape.
    That id's output metric carries no data for any unit.
    """
    start_period = extract_period_id(start_period)
    end_period = extract_period_id(end_period)

    if start_period or end_period:
        data_shape = apply_period_range(data_shape, start_period, end_period)

    effective_shape_type = shape_type
    metric_period_ids = parse_metric_periods_string(extract_metric_period_ids(metric_periods_str) or "")
    if metric_period_ids:
        data_shape = maybe_convert_periods_to_metrics(data_shape, metric_period_ids)
        effective_shape_type = "NumericSeries"

    target_table = data_shape.population_table or (table_order[0] if table_order else "")
    target_rows = tables.get(target_table, [])
    selected_ids = {r["unit_id"] for r in full_unit_set.get(target_table, [])}

    return data_shape, effective_shape_type, target_rows, selected_ids
