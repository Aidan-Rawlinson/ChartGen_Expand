"""
dispatch.py
Dispatches shape-generic operations (population-filtering, autotable stats)
to the correct shape-specific function based on the shape instance's type.
"""

from core.shared.normalisation_containers.shapes.numeric_series import (
    NumericSeries, filter_numeric_series, numeric_series_autotable_stats,
)
from core.shared.normalisation_containers.shapes.numeric_compositional import (
    NumericCompositional, filter_numeric_compositional,
    numeric_compositional_autotable_stats,
)
from core.shared.normalisation_containers.shapes.categorical_compositional import (
    CategoricalCompositional, filter_categorical_compositional,
    categorical_autotable_stats,
)
from core.shared.normalisation_containers.shapes.timeseries import (
    TimeSeries, filter_time_series, time_series_autotable_stats,
    filter_time_series_periods,
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
    raise TypeError(f"Unknown shape type: {type(shape)}")


def apply_period_range(shape, start_period_id: str = "", end_period_id: str = ""):
    """
    Trim a shape to a period_id range, ahead of any population-layer
    filtering — a normalisation step at the boundary, not a charting
    concern (Primer, Section 4). No-op for any shape without a period axis;
    only TimeSeries carries one.
    """
    if isinstance(shape, TimeSeries):
        return filter_time_series_periods(shape, start_period_id, end_period_id)
    return shape


def autotable_stats(shape) -> dict:
    """Dispatch to the correct autotable-stats function based on shape type."""
    if isinstance(shape, NumericSeries):
        return numeric_series_autotable_stats(shape)
    elif isinstance(shape, NumericCompositional):
        return numeric_compositional_autotable_stats(shape)
    elif isinstance(shape, CategoricalCompositional):
        return categorical_autotable_stats(shape)
    elif isinstance(shape, TimeSeries):
        return time_series_autotable_stats(shape)
    raise TypeError(f"Unknown shape type: {type(shape)}")
