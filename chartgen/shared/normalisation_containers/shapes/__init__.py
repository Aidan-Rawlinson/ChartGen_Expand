"""
shapes/
The five canonical data shapes: NumericSeries, NumericCompositional,
CategoricalCompositional, TimeSeries and PairedSurveyData. One module each,
plus common.py for the shared Unit/ShapeStats base, dispatch.py for the
shape-generic operations, and reference_ids.py for id-tagged stat rows.
This __init__ re-exports the full public API.

Each shape module owns its own calculation-phase logic, independent of any
visualisation: the canonical Metric-Series stats computation (compute_*),
used both at first build from API data and at population-filter
recalculation, and the shape's summary statistics (*_summary_stats).

PairedSurveyData has no REFERENCE_ROW_CONVERTERS entry, so it does not
participate in Stat Tags. Its dispatch wiring is otherwise complete.
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
