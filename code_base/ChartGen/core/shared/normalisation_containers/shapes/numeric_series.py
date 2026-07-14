"""
numeric_series.py
NumericSeries — one or more independent numeric Metric-Series, one value per
unit per metric — with its stats recalculation and population-filtering.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from core.shared.normalisation_containers.shapes.common import Unit, ShapeStats


@dataclass
class NumericSeriesMetricStats:
    """Metric-Series-level stats for a NumericSeries shape."""
    count_with_data:    Optional[int]   = None
    count_null:         Optional[int]   = None
    mean:               Optional[float] = None
    median:             Optional[float] = None
    q1:                 Optional[float] = None
    q3:                 Optional[float] = None
    min:                Optional[float] = None
    max:                Optional[float] = None


@dataclass
class NumericSeriesUnit(Unit):
    """One unit's values across one or more independent Metric-Series."""
    values: list[Optional[float]] = field(default_factory=list)


@dataclass
class NumericSeries:
    """One or more independent numeric Metric-Series across a population."""
    # Metadata
    title:              Optional[str]       = None
    metric_names:       list[str]           = field(default_factory=list)  # one per Metric-Series
    year:               Optional[int]       = None
    format_modifier:    Optional[str]       = None
    population_label:   Optional[str]       = None  # resolved population-string token label, set by build_population_layers

    # Data
    has_valid_unit_data: bool               = True
    units:              list[NumericSeriesUnit] = field(default_factory=list)

    # Stats — shape level, then one Metric-Series stats block per series
    shape_stats:        ShapeStats          = field(default_factory=ShapeStats)
    metric_stats:       list[NumericSeriesMetricStats] = field(default_factory=list)


def _percentile(sorted_values, pct):
    """Linear-interpolated percentile of a pre-sorted, non-empty value list."""
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


def compute_numeric_series_metric_stats(values: list) -> "NumericSeriesMetricStats":
    """
    Compute NumericSeriesMetricStats for one Metric-Series' value list (Nones
    included). The single canonical implementation — used both when a shape is
    first built from API data and when it is recalculated after population
    filtering.
    """
    non_null = sorted(v for v in values if v is not None)
    n = len(non_null)
    count_null = len(values) - n
    if n == 0:
        return NumericSeriesMetricStats(count_with_data=0, count_null=count_null)
    return NumericSeriesMetricStats(
        count_with_data=n,
        count_null=count_null,
        mean=round(sum(non_null) / n, 4),
        median=round(_percentile(non_null, 50), 4),
        q1=round(_percentile(non_null, 25), 4),
        q3=round(_percentile(non_null, 75), 4),
        min=round(non_null[0], 4),
        max=round(non_null[-1], 4),
    )


def _recalc_numeric_series_stats(units: list) -> list:
    """Recalculate NumericSeriesMetricStats for a filtered unit list, one per Metric-Series."""
    if not units:
        return []
    n_metrics = len(units[0].values)
    return [
        compute_numeric_series_metric_stats([u.values[m] for u in units])
        for m in range(n_metrics)
    ]


def numeric_series_autotable_stats(shape: "NumericSeries") -> dict:
    """
    Autotable statistics for a NumericSeries shape — everything on tap,
    independent of any visualisation. Keyed by Metric-Series name:
    {metric_name: {n, No data, Min, Lower Quartile, Mean, Median,
    Upper Quartile, Max}}.
    """
    out = {}
    for i, ms in enumerate(shape.metric_stats):
        name = shape.metric_names[i] if i < len(shape.metric_names) else f"Series {i + 1}"
        out[name] = {
            "n":              ms.count_with_data,
            "No data":        ms.count_null,
            "Min":            ms.min,
            "Lower Quartile": ms.q1,
            "Mean":           ms.mean,
            "Median":         ms.median,
            "Upper Quartile": ms.q3,
            "Max":            ms.max,
        }
    return out


def filter_numeric_series(shape: "NumericSeries", unit_ids: set) -> "NumericSeries":
    """Return a new NumericSeries filtered to unit_ids with stats recalculated."""
    filtered_units = [u for u in shape.units if u.unit_id in unit_ids]
    new_stats = _recalc_numeric_series_stats(filtered_units)
    new_shape_stats = ShapeStats(
        count_metric_series=len(shape.metric_names),
        count_units=len(filtered_units),
        count_units_with_any_data=sum(1 for u in filtered_units if any(v is not None for v in u.values)),
    )
    return replace(shape, units=filtered_units, metric_stats=new_stats, shape_stats=new_shape_stats)
