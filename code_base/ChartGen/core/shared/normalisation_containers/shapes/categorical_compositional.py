"""
categorical_compositional.py
CategoricalCompositional — one or more Metric-Series (questions) with
categorical Component-Series summing to a whole (e.g. yes/no, ethnicity
breakdown) — with its stats recalculation and population-filtering.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from core.shared.normalisation_containers.shapes.common import Unit, ShapeStats


@dataclass
class CategoricalCompositionalMetricStats:
    """Metric-Series-level stats for a CategoricalCompositional shape."""
    count_with_data:            Optional[int]           = None  # units that gave a response
    count_null:                 Optional[int]            = None  # units with no response
    component_counts:           list[Optional[int]]     = field(default_factory=list)  # one count per category


@dataclass
class CategoricalCompositionalUnit(Unit):
    """One unit's response for one Metric-Series (question)."""
    response: Optional[str] = None


@dataclass
class CategoricalCompositionalMetric:
    """One Metric-Series (question) within a CategoricalCompositional shape."""
    name:               Optional[str]                           = None
    category_names:     list[str]                               = field(default_factory=list)
    units:              list[CategoricalCompositionalUnit]      = field(default_factory=list)
    stats:              CategoricalCompositionalMetricStats     = field(default_factory=CategoricalCompositionalMetricStats)


@dataclass
class CategoricalCompositional:
    """One or more Metric-Series (questions) per population, each with categorical Component-Series that sum to a whole."""
    # Metadata
    title:              Optional[str]       = None
    year:               Optional[int]       = None
    population_label:   Optional[str]       = None  # resolved population-string token label, set by build_population_layers

    # Data — one CategoricalCompositionalMetric per question/Metric-Series
    has_valid_unit_data: bool               = True
    metrics:            list[CategoricalCompositionalMetric] = field(default_factory=list)

    # Shape-level stats
    shape_stats:        ShapeStats          = field(default_factory=ShapeStats)


def compute_categorical_metric_stats(units: list, category_names: list) -> "CategoricalCompositionalMetricStats":
    """
    Compute CategoricalCompositionalMetricStats for one Metric-Series'
    (question's) unit list. The single canonical implementation — used both
    when a shape is first built from API data and when it is recalculated
    after population filtering.
    """
    responses = [u.response for u in units]
    n_with = sum(1 for r in responses if r is not None)
    n_null = len(responses) - n_with
    counts = [sum(1 for r in responses if r == cat) for cat in category_names]
    return CategoricalCompositionalMetricStats(
        count_with_data=n_with, count_null=n_null, component_counts=counts,
    )


def categorical_autotable_stats(shape: "CategoricalCompositional") -> dict:
    """
    Autotable statistics for a CategoricalCompositional shape — everything on
    tap, independent of any visualisation: response counts and each
    category's share of responses. Keyed by Metric-Series (question) name:
    {question: {n, No response, Categories: {category: {Count, %}}}}.
    """
    out = {}
    for metric in shape.metrics:
        n = metric.stats.count_with_data or 0
        categories = {}
        for i, name in enumerate(metric.category_names):
            counts = metric.stats.component_counts
            count = (counts[i] or 0) if i < len(counts) else 0
            pct = round(count / n * 100, 4) if n else None
            categories[name] = {"Count": count, "%": pct}
        out[metric.name or "Question"] = {
            "n":           n,
            "No response": metric.stats.count_null,
            "Categories":  categories,
        }
    return out


def filter_categorical_compositional(shape: "CategoricalCompositional", unit_ids: set) -> "CategoricalCompositional":
    """Return a new CategoricalCompositional filtered to unit_ids with stats recalculated."""
    new_metrics = []
    for metric in shape.metrics:
        filtered_units = [u for u in metric.units if u.unit_id in unit_ids]
        new_stats = compute_categorical_metric_stats(filtered_units, metric.category_names)
        new_metrics.append(replace(metric, units=filtered_units, stats=new_stats))
    n_units = len(new_metrics[0].units) if new_metrics else 0
    new_shape_stats = ShapeStats(
        count_metric_series=len(new_metrics),
        count_units=n_units,
        count_units_with_any_data=new_metrics[0].stats.count_with_data if new_metrics else 0,
    )
    return replace(shape, metrics=new_metrics, shape_stats=new_shape_stats)
