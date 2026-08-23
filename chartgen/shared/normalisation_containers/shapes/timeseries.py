"""
timeseries.py
TimeSeries — one or more independent numeric Metric-Series, one value per
unit per metric per period, across a shared period axis.

The period axis lives once on the shape, not per metric. Two metrics that
did not share a period axis would not be one dataset, and would need two
shapes.

API-supplied period stats (dateAverages, dateMedians,
calculatedNationalAverages) are not carried onto this shape. Stats are
recomputed locally per period from the raw per-unit values, against
whatever population layer is resolved.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from chartgen.shared.normalisation_containers.shapes.common import Unit, ShapeStats


@dataclass
class TimeSeriesPeriod:
    """One point on the shared period axis — id plus its display label."""
    period_id:    str
    period_label: str


@dataclass
class TimeSeriesMetricPeriodStats:
    """Stats for one Metric-Series at one period — same fields as NumericSeriesMetricStats, computed per period rather than once for the whole series."""
    count_with_data:    Optional[int]   = None
    count_null:         Optional[int]   = None
    mean:               Optional[float] = None
    median:             Optional[float] = None
    q1:                 Optional[float] = None
    q3:                 Optional[float] = None
    min:                Optional[float] = None
    max:                Optional[float] = None


@dataclass
class TimeSeriesUnit(Unit):
    """One unit's values for one Metric-Series, parallel to the shape's periods list — same index, same order. None where the unit has no value for that period."""
    values: list[Optional[float]] = field(default_factory=list)


@dataclass
class TimeSeriesMetric:
    """One Metric-Series within a TimeSeries shape."""
    name:         Optional[str]                 = None
    units:        list[TimeSeriesUnit]           = field(default_factory=list)
    period_stats: list[TimeSeriesMetricPeriodStats] = field(default_factory=list)  # parallel to shape.periods


@dataclass
class TimeSeries:
    """One or more independent numeric Metric-Series across a population, each value indexed by unit and by a shared period axis."""
    # Descriptive fields
    title:              Optional[str]       = None
    format_modifier:    Optional[str]       = None
    population_label:   Optional[str]       = None  # resolved population-string token label, set by build_population_layers
    population_table:   Optional[str]       = None  # name of the population table this data's units belong to

    # Travels with the shape without being part of it. Not in the
    # chart_inputs contract. Carries through filtering and replace().
    metadata:           dict                = field(default_factory=lambda: {"source_url": None})

    # Period axis — shared across every Metric-Series in this shape
    periods:            list[TimeSeriesPeriod] = field(default_factory=list)

    # Data
    has_valid_unit_data: bool               = True
    metrics:            list[TimeSeriesMetric] = field(default_factory=list)

    # Stats — shape level only; per-period, per-metric stats live on each TimeSeriesMetric
    shape_stats:        ShapeStats          = field(default_factory=ShapeStats)


def _percentile(sorted_values, pct):
    """Linear-interpolated percentile of a pre-sorted, non-empty value list. Each shape module owns its own copy of its stats computation."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    idx = (pct / 100) * (n - 1)
    lo = int(idx)
    hi = lo + 1
    frac = idx - lo
    if hi >= n:
        return sorted_values[-1]
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def compute_time_series_period_stats(values: list) -> "TimeSeriesMetricPeriodStats":
    """
    Compute TimeSeriesMetricPeriodStats for one Metric-Series' value list at
    one period (Nones included). The single canonical implementation — used
    both when a shape is first built from API data and when it is
    recalculated after population filtering.
    """
    non_null = sorted(v for v in values if v is not None)
    n = len(non_null)
    count_null = len(values) - n
    if n == 0:
        return TimeSeriesMetricPeriodStats(count_with_data=0, count_null=count_null)
    return TimeSeriesMetricPeriodStats(
        count_with_data=n,
        count_null=count_null,
        mean=round(sum(non_null) / n, 4),
        median=round(_percentile(non_null, 50), 4),
        q1=round(_percentile(non_null, 25), 4),
        q3=round(_percentile(non_null, 75), 4),
        min=round(non_null[0], 4),
        max=round(non_null[-1], 4),
    )


def _recalc_time_series_period_stats(units: list, n_periods: int) -> list:
    """Recalculate TimeSeriesMetricPeriodStats for a filtered unit list, one per period."""
    return [
        compute_time_series_period_stats([u.values[p] for u in units if p < len(u.values)])
        for p in range(n_periods)
    ]


def time_series_summary_stats(shape: "TimeSeries") -> dict:
    """
    Summary statistics for a TimeSeries shape — keyed by Metric-Series
    name, then by period label:
    {metric_name: {period_label: {n, No data, Min, Lower Quartile, Mean,
    Median, Upper Quartile, Max}}}.
    """
    out = {}
    for metric in shape.metrics:
        name = metric.name or "Metric"
        per_period = {}
        for i, period in enumerate(shape.periods):
            stats = metric.period_stats[i] if i < len(metric.period_stats) else TimeSeriesMetricPeriodStats()
            per_period[period.period_label] = {
                "n":              stats.count_with_data,
                "No data":        stats.count_null,
                "Min":            stats.min,
                "Lower Quartile": stats.q1,
                "Mean":           stats.mean,
                "Median":         stats.median,
                "Upper Quartile": stats.q3,
                "Max":            stats.max,
            }
        out[name] = per_period
    return out


def filter_time_series_periods(shape: "TimeSeries", start_period_id: str = "",
                                end_period_id: str = "") -> "TimeSeries":
    """
    Return a new TimeSeries trimmed to the inclusive period_id range. A blank
    id at either end means from the first, or to the last, period.

    No stats are recalculated. Each period's stats are already independent of
    every other, so this is a pure slice of periods, each metric's values,
    and period_stats down to the same index range.

    An id given but not found falls back to that end of the shape's own
    period axis, the same as a blank: an unresolvable start means from the
    first period, an unresolvable end means to the last. An unresolvable
    period is a no-data case, not an error — the row renders what the shape
    actually has, rather than failing or discarding the bound at the other
    end. This happens in practice, and what it needs is a person reviewing
    the output, not a blank row.

    Only a start resolving after the end produces an empty range.
    """
    ids_in_order = [p.period_id for p in shape.periods]

    start_idx = ids_in_order.index(start_period_id) if start_period_id in ids_in_order else 0
    end_idx = (ids_in_order.index(end_period_id) if end_period_id in ids_in_order
               else len(ids_in_order) - 1)

    if start_idx > end_idx:
        new_periods = []
        new_metrics = [replace(m, units=[replace(u, values=[]) for u in m.units], period_stats=[])
                       for m in shape.metrics]
    else:
        new_periods = shape.periods[start_idx:end_idx + 1]
        new_metrics = [
            replace(
                m,
                units=[replace(u, values=u.values[start_idx:end_idx + 1]) for u in m.units],
                period_stats=m.period_stats[start_idx:end_idx + 1],
            )
            for m in shape.metrics
        ]

    new_shape_stats = replace(
        shape.shape_stats,
        count_units_with_any_data=sum(
            1 for u in (new_metrics[0].units if new_metrics else [])
            if any(v is not None for v in u.values)
        ) if new_metrics else 0,
    )
    return replace(shape, periods=new_periods, metrics=new_metrics, shape_stats=new_shape_stats)


def filter_time_series(shape: "TimeSeries", unit_ids: set) -> "TimeSeries":
    """Return a new TimeSeries filtered to unit_ids with per-period stats recalculated for every Metric-Series."""
    n_periods = len(shape.periods)
    new_metrics = []
    for metric in shape.metrics:
        filtered_units = [u for u in metric.units if u.unit_id in unit_ids]
        new_period_stats = _recalc_time_series_period_stats(filtered_units, n_periods)
        new_metrics.append(replace(metric, units=filtered_units, period_stats=new_period_stats))
    n_units = len(new_metrics[0].units) if new_metrics else 0
    new_shape_stats = ShapeStats(
        count_metric_series=len(new_metrics),
        count_units=n_units,
        count_units_with_any_data=sum(
            1 for u in (new_metrics[0].units if new_metrics else [])
            if any(v is not None for v in u.values)
        ),
    )
    return replace(shape, metrics=new_metrics, shape_stats=new_shape_stats)
