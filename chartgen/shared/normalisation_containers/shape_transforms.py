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

from chartgen.shared.normalisation_containers.shapes.common import ShapeStats
from chartgen.shared.normalisation_containers.shapes.timeseries import TimeSeries
from chartgen.shared.normalisation_containers.shapes.numeric_series import (
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
    metadata, and has_valid_unit_data carry across unchanged. year is left
    None -- TimeSeries/Indicators data has no year of its own (Architecture,
    Decision 10), so there's nothing meaningful to set it to.

    A period_id not present on the shape (a typo, or a period this
    report's own data simply doesn't have -- see Decisions.md) is not
    treated as an error. Rather than refuse to produce a shape at all, it
    becomes its own output metric with every unit's value set to None --
    the same "no data" state any other missing value already produces
    everywhere downstream (every Base Chart already handles a metric with
    no data for some or all units gracefully -- see the chart_inputs
    contract). Whether and how to represent that visually is each Base
    Chart's own concern, not something resolved here; ChartGen's job is
    to hand over the data faithfully, including the fact that this
    particular period doesn't exist for this report. A missing id keeps
    its own given position among that metric's output columns (after
    every id that *did* resolve, in their shape-chronological order) --
    there's no chronological position to sort it into, since it isn't a
    real period on this shape at all. Its label falls back to the bare
    id itself, in parentheses, since there's no period_label to read.
    """
    index_by_id = {p.period_id: i for i, p in enumerate(shape.periods)}
    found_ids = [pid for pid in period_ids if pid in index_by_id]
    missing_ids = list(dict.fromkeys(pid for pid in period_ids if pid not in index_by_id))

    # Dedupe, then chronological order (the shape's own period order), not
    # whatever order period_ids happen to be given in.
    selected_indices = sorted({index_by_id[pid] for pid in found_ids})

    # Master unit population — union across all source metrics, first-seen order.
    master_order = []
    seen_ids = set()
    for metric in shape.metrics:
        for u in metric.units:
            if u.unit_id not in seen_ids:
                seen_ids.add(u.unit_id)
                master_order.append((u.unit_id, u.unit_code))

    # Output columns: (metric, period_index-or-None) pairs, metric-major --
    # every resolved period first (shape-chronological order), then every
    # unresolved id (its own given order), per metric.
    columns = []
    metric_names = []
    for metric in shape.metrics:
        unit_by_id = {u.unit_id: u for u in metric.units}
        for idx in selected_indices:
            columns.append((unit_by_id, idx))
            period_label = shape.periods[idx].period_label
            metric_names.append(f"{metric.name or 'Metric'} ({period_label})")
        for pid in missing_ids:
            columns.append((unit_by_id, None))
            metric_names.append(f"{metric.name or 'Metric'} ({pid})")

    numeric_units = []
    for unit_id, unit_code in master_order:
        values = []
        for unit_by_id, period_idx in columns:
            if period_idx is None:
                values.append(None)
                continue
            src_unit = unit_by_id.get(unit_id)
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
        metadata=shape.metadata,
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
