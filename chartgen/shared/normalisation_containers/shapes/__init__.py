"""
shapes/
Canonical data shapes for ChartGen — NumericSeries, NumericCompositional,
CategoricalCompositional, TimeSeries, and PairedSurveyData — split into one
module per shape (plus a common.py for the shared Unit/ShapeStats base, a
dispatch.py for filter_shape/summary_stats, and a reference_ids.py for
id-tagged stat rows). This __init__ re-exports the full public API so
external call sites are unaffected by the split.

PairedSurveyData is not yet wired into reference_ids.py (Summary Stat Tags)
— no REFERENCE_ROW_CONVERTERS entry exists for it yet. Its
summary_stats()/dispatch.py wiring is otherwise complete.

Each shape module owns the calculation-phase logic for its shape,
independent of any visualisation: the single canonical Metric-Series stats
computation (compute_*_stats, used both at first build from API data and at
population-filter recalculation) and the shape's summary statistics
(*_summary_stats). Renamed from *_autotable_stats this session — these read
existing stats off a shape, independent of the (separate, not yet built)
Autotables feature, which will eventually draw on these or on the shapes
directly.

TimeSeries is wired into dispatch.py's filter_shape/summary_stats and into
population_layers.build_population_layers, the same as every other shape —
chart_type_map.csv now has a TimeSeries row (period_line_chart), so the
generic dispatch points are called with a TimeSeries instance in the normal
course of rendering.
"""

from chartgen.shared.normalisation_containers.shapes.common import Unit, ShapeStats

from chartgen.shared.normalisation_containers.shapes.numeric_series import (
    NumericSeriesMetricStats,
    NumericSeriesUnit,
    NumericSeries,
    compute_numeric_series_metric_stats,
    numeric_series_summary_stats,
    filter_numeric_series,
)
from chartgen.shared.normalisation_containers.shapes.numeric_compositional import (
    NumericCompositionalMetricStats,
    NumericCompositionalUnit,
    NumericCompositionalMetric,
    NumericCompositional,
    compute_numeric_compositional_metric_stats,
    numeric_compositional_summary_stats,
    filter_numeric_compositional,
)
from chartgen.shared.normalisation_containers.shapes.categorical_compositional import (
    CategoricalCompositionalMetricStats,
    CategoricalCompositionalUnit,
    CategoricalCompositionalMetric,
    CategoricalCompositional,
    compute_categorical_metric_stats,
    categorical_summary_stats,
    filter_categorical_compositional,
)
from chartgen.shared.normalisation_containers.shapes.dispatch import (
    filter_shape,
    summary_stats,
    summary_stats_by_layer,
    shape_units,
    units_by_layer,
    unit_has_data,
    apply_period_range,
)
from chartgen.shared.normalisation_containers.shapes.timeseries import (
    TimeSeriesPeriod,
    TimeSeriesMetricPeriodStats,
    TimeSeriesUnit,
    TimeSeriesMetric,
    TimeSeries,
    compute_time_series_period_stats,
    time_series_summary_stats,
    filter_time_series,
    filter_time_series_periods,
)
from chartgen.shared.normalisation_containers.shapes.paired_survey_data import (
    PairedObservation,
    PairedSurveyDataUnit,
    PairedSurveyDataStats,
    PairedSurveyData,
    compute_paired_survey_data_stats,
    paired_survey_data_summary_stats,
    filter_paired_survey_data,
)
from chartgen.shared.normalisation_containers.shapes.reference_ids import (
    reference_rows_for_shape_type,
)

__all__ = [
    "Unit",
    "ShapeStats",
    "NumericSeriesMetricStats",
    "NumericSeriesUnit",
    "NumericSeries",
    "compute_numeric_series_metric_stats",
    "numeric_series_summary_stats",
    "filter_numeric_series",
    "NumericCompositionalMetricStats",
    "NumericCompositionalUnit",
    "NumericCompositionalMetric",
    "NumericCompositional",
    "compute_numeric_compositional_metric_stats",
    "numeric_compositional_summary_stats",
    "filter_numeric_compositional",
    "CategoricalCompositionalMetricStats",
    "CategoricalCompositionalUnit",
    "CategoricalCompositionalMetric",
    "CategoricalCompositional",
    "compute_categorical_metric_stats",
    "categorical_summary_stats",
    "filter_categorical_compositional",
    "TimeSeriesPeriod",
    "TimeSeriesMetricPeriodStats",
    "TimeSeriesUnit",
    "TimeSeriesMetric",
    "TimeSeries",
    "compute_time_series_period_stats",
    "time_series_summary_stats",
    "filter_time_series",
    "filter_time_series_periods",
    "filter_shape",
    "summary_stats",
    "summary_stats_by_layer",
    "shape_units",
    "units_by_layer",
    "unit_has_data",
    "apply_period_range",
    "PairedObservation",
    "PairedSurveyDataUnit",
    "PairedSurveyDataStats",
    "PairedSurveyData",
    "compute_paired_survey_data_stats",
    "paired_survey_data_summary_stats",
    "filter_paired_survey_data",
    "reference_rows_for_shape_type",
]
