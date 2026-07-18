"""
shapes/
Canonical data shapes for ChartGen — NumericSeries, NumericCompositional,
CategoricalCompositional, and TimeSeries — split into one module per shape
(plus a common.py for the shared Unit/ShapeStats base and a dispatch.py for
filter_shape/autotable_stats). This __init__ re-exports the full public API
so external call sites are unaffected by the split.

Each shape module owns the calculation-phase logic for its shape,
independent of any visualisation: the single canonical Metric-Series stats
computation (compute_*_stats, used both at first build from API data and at
population-filter recalculation) and the shape's autotable statistics
(*_autotable_stats).

TimeSeries is wired into dispatch.py's filter_shape/autotable_stats and into
population_layers.build_population_layers, the same as every other shape —
chart_type_map.csv now has a TimeSeries row (period_line_chart), so the
generic dispatch points are called with a TimeSeries instance in the normal
course of rendering.
"""

from core.shared.normalisation_containers.shapes.common import Unit, ShapeStats

from core.shared.normalisation_containers.shapes.numeric_series import (
    NumericSeriesMetricStats,
    NumericSeriesUnit,
    NumericSeries,
    compute_numeric_series_metric_stats,
    numeric_series_autotable_stats,
    filter_numeric_series,
)
from core.shared.normalisation_containers.shapes.numeric_compositional import (
    NumericCompositionalMetricStats,
    NumericCompositionalUnit,
    NumericCompositionalMetric,
    NumericCompositional,
    compute_numeric_compositional_metric_stats,
    numeric_compositional_autotable_stats,
    filter_numeric_compositional,
)
from core.shared.normalisation_containers.shapes.categorical_compositional import (
    CategoricalCompositionalMetricStats,
    CategoricalCompositionalUnit,
    CategoricalCompositionalMetric,
    CategoricalCompositional,
    compute_categorical_metric_stats,
    categorical_autotable_stats,
    filter_categorical_compositional,
)
from core.shared.normalisation_containers.shapes.dispatch import (
    filter_shape,
    autotable_stats,
    apply_period_range,
)
from core.shared.normalisation_containers.shapes.timeseries import (
    TimeSeriesPeriod,
    TimeSeriesMetricPeriodStats,
    TimeSeriesUnit,
    TimeSeriesMetric,
    TimeSeries,
    compute_time_series_period_stats,
    time_series_autotable_stats,
    filter_time_series,
    filter_time_series_periods,
)

__all__ = [
    "Unit",
    "ShapeStats",
    "NumericSeriesMetricStats",
    "NumericSeriesUnit",
    "NumericSeries",
    "compute_numeric_series_metric_stats",
    "numeric_series_autotable_stats",
    "filter_numeric_series",
    "NumericCompositionalMetricStats",
    "NumericCompositionalUnit",
    "NumericCompositionalMetric",
    "NumericCompositional",
    "compute_numeric_compositional_metric_stats",
    "numeric_compositional_autotable_stats",
    "filter_numeric_compositional",
    "CategoricalCompositionalMetricStats",
    "CategoricalCompositionalUnit",
    "CategoricalCompositionalMetric",
    "CategoricalCompositional",
    "compute_categorical_metric_stats",
    "categorical_autotable_stats",
    "filter_categorical_compositional",
    "TimeSeriesPeriod",
    "TimeSeriesMetricPeriodStats",
    "TimeSeriesUnit",
    "TimeSeriesMetric",
    "TimeSeries",
    "compute_time_series_period_stats",
    "time_series_autotable_stats",
    "filter_time_series",
    "filter_time_series_periods",
    "filter_shape",
    "autotable_stats",
    "apply_period_range",
]
