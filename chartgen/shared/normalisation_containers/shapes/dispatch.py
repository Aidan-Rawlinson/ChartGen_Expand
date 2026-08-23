"""
dispatch.py
Dispatches shape-generic operations (population-filtering, summary stats)
to the correct shape-specific function based on the shape instance's type.
"""

from chartgen.shared.normalisation_containers.shapes.numeric_series import (
    NumericSeries, filter_numeric_series, numeric_series_summary_stats,
)
from chartgen.shared.normalisation_containers.shapes.numeric_compositional import (
    NumericCompositional, filter_numeric_compositional,
    numeric_compositional_summary_stats,
)
from chartgen.shared.normalisation_containers.shapes.categorical_compositional import (
    CategoricalCompositional, filter_categorical_compositional,
    categorical_summary_stats,
)
from chartgen.shared.normalisation_containers.shapes.timeseries import (
    TimeSeries, filter_time_series, time_series_summary_stats,
    filter_time_series_periods,
)
from chartgen.shared.normalisation_containers.shapes.paired_survey_data import (
    PairedSurveyData, filter_paired_survey_data, paired_survey_data_summary_stats,
)


def filter_shape(shape, unit_ids: set):
    """Dispatch to the correct filter function based on shape type."""
    if isinstance(shape, NumericSeries):
        return filter_numeric_series(shape, unit_ids)
    elif isinstance(shape, NumericCompositional):
        return filter_numeric_compositional(shape, unit_ids)
    elif isinstance(shape, CategoricalCompositional):
        return filter_categorical_compositional(shape, unit_ids)
    elif isinstance(shape, TimeSeries):
        return filter_time_series(shape, unit_ids)
    elif isinstance(shape, PairedSurveyData):
        return filter_paired_survey_data(shape, unit_ids)
    raise TypeError(f"Unknown shape type: {type(shape)}")


def apply_period_range(shape, start_period_id: str = "", end_period_id: str = ""):
    """
    Trim a shape to a period_id range, ahead of any population-layer
    filtering. No-op for any shape without a period axis; only TimeSeries
    has one.
    """
    if isinstance(shape, TimeSeries):
        return filter_time_series_periods(shape, start_period_id, end_period_id)
    return shape


def summary_stats(shape) -> dict:
    """Dispatch to the correct summary-stats function based on shape type."""
    if isinstance(shape, NumericSeries):
        return numeric_series_summary_stats(shape)
    elif isinstance(shape, NumericCompositional):
        return numeric_compositional_summary_stats(shape)
    elif isinstance(shape, CategoricalCompositional):
        return categorical_summary_stats(shape)
    elif isinstance(shape, TimeSeries):
        return time_series_summary_stats(shape)
    elif isinstance(shape, PairedSurveyData):
        return paired_survey_data_summary_stats(shape)
    raise TypeError(f"Unknown shape type: {type(shape)}")


def summary_stats_by_layer(population_layers: list) -> dict:
    """
    Summary stats for every population layer passed to a chart, keyed by
    each layer's own population_label — the correction this exists for:
    Base Chart functions only ever read stats off population_layers[0]
    (the scope); every other layer's own stats were never read at all.
    Reads only what each shape instance already computes for itself;
    nothing here is calculated afresh.
    """
    return {layer.population_label: summary_stats(layer) for layer in population_layers}


def shape_units(shape) -> list:
    """
    Return the Unit-like objects making up a shape's population.

    NumericSeries and PairedSurveyData carry a single shape-level units
    list. The other three carry one per metric-series, but every
    metric-series in one shape instance shares the same population, so
    metrics[0].units stands in for the whole shape.
    """
    if isinstance(shape, (NumericSeries, PairedSurveyData)):
        return shape.units
    elif isinstance(shape, (NumericCompositional, CategoricalCompositional, TimeSeries)):
        return shape.metrics[0].units if shape.metrics else []
    raise TypeError(f"Unknown shape type: {type(shape)}")


def units_by_layer(population_layers: list) -> dict:
    """Units for every population layer passed to a chart, keyed by each layer's own population_label."""
    return {layer.population_label: shape_units(layer) for layer in population_layers}


def unit_has_data(unit) -> bool:
    """
    Whether a unit has actual data for this chart, rather than being a
    "no data" submission — the same distinction count_units_with_any_data
    already makes at shape level, exposed here per unit. NumericSeries,
    NumericCompositional, and TimeSeries units carry a `values` list (any
    entry present counts as data); CategoricalCompositionalUnit carries a
    single `response` field instead; PairedSurveyDataUnit carries a
    `records` list (any record with a start or end value counts as data).
    """
    if hasattr(unit, "values"):
        return any(v is not None for v in unit.values)
    if hasattr(unit, "response"):
        return unit.response is not None
    if hasattr(unit, "records"):
        return any(r.start_value is not None or r.end_value is not None for r in unit.records)
    return False
