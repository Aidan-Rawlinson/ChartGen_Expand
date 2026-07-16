"""
numeric_compositional.py
NumericCompositional — one or more Metric-Series whose Component-Series sum
to a whole (e.g. radar/spider chart data) — with its stats recalculation and
population-filtering.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from core.shared.normalisation_containers.shapes.common import Unit, ShapeStats


@dataclass
class NumericCompositionalMetricStats:
    """Metric-Series-level stats for a NumericCompositional shape."""
    count_with_data:        Optional[int]           = None  # units with at least one non-null component
    count_null:             Optional[int]            = None  # units with all components null
    component_counts_with_data: list[Optional[int]] = field(default_factory=list)  # one per Component-Series


@dataclass
class NumericCompositionalUnit(Unit):
    """One unit's values for one Metric-Series in a NumericCompositional shape."""
    values: list[Optional[float]] = field(default_factory=list)


@dataclass
class NumericCompositionalMetric:
    """One Metric-Series within a NumericCompositional shape."""
    name:               Optional[str]                       = None
    component_names:    list[str]                           = field(default_factory=list)
    units:              list[NumericCompositionalUnit]      = field(default_factory=list)
    stats:              NumericCompositionalMetricStats     = field(default_factory=NumericCompositionalMetricStats)


@dataclass
class NumericCompositional:
    """One or more Metric-Series per unit, each composed of Component-Series summing to a whole."""
    # Metadata
    title:              Optional[str]       = None
    year:               Optional[int]       = None
    format_modifier:    Optional[str]       = None
    population_label:   Optional[str]       = None  # resolved population-string token label, set by build_population_layers
    population_table:   Optional[str]       = None  # name of the population table this data's units belong to (e.g. "submissions_2026_123", "nhs_organisations") — a plain reference to an existing table name, not derived at read time

    # Data — one NumericCompositionalMetric per Metric-Series
    has_valid_unit_data: bool               = True
    metrics:            list[NumericCompositionalMetric] = field(default_factory=list)

    # Shape-level stats
    shape_stats:        ShapeStats          = field(default_factory=ShapeStats)


def compute_numeric_compositional_metric_stats(units: list) -> "NumericCompositionalMetricStats":
    """
    Compute NumericCompositionalMetricStats for one Metric-Series' unit list.
    The single canonical implementation — used both when a shape is first
    built from API data and when it is recalculated after population filtering.
    """
    n_with = sum(1 for u in units if any(v is not None for v in u.values))
    n_null = len(units) - n_with
    n_comp = len(units[0].values) if units else 0
    comp_counts = []
    for c in range(n_comp):
        comp_counts.append(sum(1 for u in units if c < len(u.values) and u.values[c] is not None))
    return NumericCompositionalMetricStats(
        count_with_data=n_with, count_null=n_null,
        component_counts_with_data=comp_counts,
    )


def numeric_compositional_autotable_stats(shape: "NumericCompositional") -> dict:
    """
    Autotable statistics for a NumericCompositional shape — everything on
    tap, independent of any visualisation: raw component values, their sum,
    and each component's share of that sum. Keyed by Metric-Series name:
    {metric_name: {Total, Components: {component: {Value, %}}}}.
    """
    out = {}
    for metric in shape.metrics:
        values = metric.units[0].values if metric.units else []
        total = sum(v for v in values if v is not None)
        components = {}
        for i, v in enumerate(values):
            name = metric.component_names[i] if i < len(metric.component_names) else f"Component {i + 1}"
            pct = round(v / total * 100, 4) if (v is not None and total) else None
            components[name] = {"Value": v, "%": pct}
        out[metric.name or "Metric"] = {"Total": total, "Components": components}
    return out


def filter_numeric_compositional(shape: "NumericCompositional", unit_ids: set) -> "NumericCompositional":
    """Return a new NumericCompositional filtered to unit_ids with stats recalculated."""
    new_metrics = []
    for metric in shape.metrics:
        filtered_units = [u for u in metric.units if u.unit_id in unit_ids]
        new_stats = compute_numeric_compositional_metric_stats(filtered_units)
        new_metrics.append(replace(metric, units=filtered_units, stats=new_stats))
    n_units = len(new_metrics[0].units) if new_metrics else 0
    new_shape_stats = ShapeStats(
        count_metric_series=len(new_metrics),
        count_units=n_units,
        count_units_with_any_data=n_units,
    )
    return replace(shape, metrics=new_metrics, shape_stats=new_shape_stats)
