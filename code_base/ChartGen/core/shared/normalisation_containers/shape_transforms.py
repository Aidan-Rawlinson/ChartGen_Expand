"""
shape_transforms.py
Cross-shape transforms — conversions between two different canonical data
shapes, as opposed to the same-shape filtering/recalculation each shape
module owns for itself (shapes/dispatch.py). Lives outside the shapes/
package for the same reason url_triage.py and fetch_dispatch.py sit outside
both toolkit packages (Architecture, Decision 10): something has to know
about two shapes at once without either shape module depending on the
other.

time_series_to_numeric_series() converts one or more periods on a
TimeSeries shape into a snapshot NumericSeries — one output Metric-Series
per (source Metric-Series x selected period), so the result can be handed
to any ordinary NumericSeries chart type. Applied ahead of
build_population_layers, the same normalisation-at-the-boundary point as
apply_period_range (shapes/dispatch.py) — the charting side never needs to
know a TimeSeries was ever involved.
"""

from core.shared.normalisation_containers.shapes.common import ShapeStats
from core.shared.normalisation_containers.shapes.timeseries import TimeSeries
from core.shared.normalisation_containers.shapes.numeric_series import (
    NumericSeries, NumericSeriesUnit, compute_numeric_series_metric_stats,
)


def time_series_to_numeric_series(shape: TimeSeries, period_ids: list) -> NumericSeries:
    """
    Convert a TimeSeries shape into a NumericSeries snapshot across one or
    more periods.

    Output ordering: grouped by source Metric-Series first, then by period
    within it (M1-P1, M1-P2, M2-P1, M2-P2...) — periods always in the
    shape's own trusted-chronological order, regardless of the order
    period_ids are given in. Output metric name: "{Metric-Series name}
    ({period label})".

    Unit population: built as the union of every source metric's units, in
    first-seen order (metric order, then that metric's own unit order). In
    practice every Metric-Series on one TimeSeries shares one fetch and one
    population, so this is normally just the first metric's own unit list —
    the union is a defensive measure, not an expected divergence. A unit
    missing from a given source metric contributes None for that metric's
    columns rather than being dropped from the output entirely.

    Metadata: title, format_modifier, population_table, population_label,
    and has_valid_unit_data carry across unchanged. year is left None —
    TimeSeries/Indicators data has no year of its own (Architecture,
    Decision 10), so there's nothing meaningful to set it to.

    Raises ValueError if any period_id in period_ids is not present on the
    shape (a typo or a period since dropped) — this halts the row rather
    than silently producing a narrower or wrong-shaped result.
    """
    index_by_id = {p.period_id: i for i, p in enumerate(shape.periods)}
    missing = [pid for pid in period_ids if pid not in index_by_id]
    if missing:
        raise ValueError(
            f"period_id(s) not found on this TimeSeries shape: {', '.join(missing)}"
        )

    # Dedupe, then chronological order (the shape's own period order), not
    # whatever order period_ids happen to be given in.
    selected_indices = sorted({index_by_id[pid] for pid in period_ids})

    # Master unit population — union across all source metrics, first-seen order.
    master_order = []
    seen_ids = set()
    for metric in shape.metrics:
        for u in metric.units:
            if u.unit_id not in seen_ids:
                seen_ids.add(u.unit_id)
                master_order.append((u.unit_id, u.unit_code))

    # Output columns: (metric, period_index) pairs, metric-major.
    columns = []
    metric_names = []
    for metric in shape.metrics:
        unit_by_id = {u.unit_id: u for u in metric.units}
        for idx in selected_indices:
            columns.append(unit_by_id)
            period_label = shape.periods[idx].period_label
            metric_names.append(f"{metric.name or 'Metric'} ({period_label})")

    period_index_by_column = [idx for _ in shape.metrics for idx in selected_indices]

    numeric_units = []
    for unit_id, unit_code in master_order:
        values = []
        for col_i, unit_by_id in enumerate(columns):
            src_unit = unit_by_id.get(unit_id)
            period_idx = period_index_by_column[col_i]
            values.append(
                src_unit.values[period_idx]
                if (src_unit is not None and period_idx < len(src_unit.values))
                else None
            )
        numeric_units.append(NumericSeriesUnit(unit_code=unit_code, unit_id=unit_id, values=values))

    metric_stats = [
        compute_numeric_series_metric_stats([u.values[j] for u in numeric_units])
        for j in range(len(metric_names))
    ]

    shape_stats = ShapeStats(
        count_metric_series=len(metric_names),
        count_units=len(numeric_units),
        count_units_with_any_data=sum(1 for u in numeric_units if any(v is not None for v in u.values)),
    )

    return NumericSeries(
        title=shape.title,
        metric_names=metric_names,
        year=None,
        format_modifier=shape.format_modifier,
        population_label=shape.population_label,
        population_table=shape.population_table,
        has_valid_unit_data=shape.has_valid_unit_data,
        units=numeric_units,
        shape_stats=shape_stats,
        metric_stats=metric_stats,
    )


def maybe_convert_periods_to_metrics(shape, period_ids: list):
    """
    Entry point for callers that don't want to check shape type themselves.
    No-op (returns shape unchanged) if period_ids is empty or shape isn't a
    TimeSeries — e.g. a row with no metric_periods set, or a non-TimeSeries
    cache_file with a stray value in that column.
    """
    if not period_ids or not isinstance(shape, TimeSeries):
        return shape
    return time_series_to_numeric_series(shape, period_ids)
