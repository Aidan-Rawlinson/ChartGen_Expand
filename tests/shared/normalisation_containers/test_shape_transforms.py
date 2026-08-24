"""
Tests for shared/normalisation_containers/shape_transforms.py

"Convert to Metrics" on the Charts sheet turns selected periods of a
TimeSeries into a NumericSeries snapshot, so a trend dataset can be drawn on
any NumericSeries chart type. The conversion runs before the chart is
chosen, "so the charting side never needs to know a TimeSeries was
involved".

Four documented rules, each of which would produce a wrong-but-plausible
chart if it broke:

  "periods in the shape's own chronological order regardless of the order
  period_ids are given" -- otherwise a user ticking periods in the wrong
  order gets a chart with time running backwards.

  "A unit missing from a source metric contributes None for that metric's
  columns rather than being dropped" -- otherwise a unit vanishes from the
  population because it happened to miss one metric.

  "A period_id absent from the shape is not an error. It becomes its own
  output metric with every unit's value None" -- so a period that has since
  been removed upstream shows as a gap rather than silently disappearing.

  "year is left None, since this data has no year of its own."
"""

from chartgen.shared.normalisation_containers.shape_transforms import (
    maybe_convert_periods_to_metrics,
    time_series_to_numeric_series,
)


# ---------------------------------------------------------------------------
# The basic conversion
# ---------------------------------------------------------------------------

def test_one_selected_period_becomes_one_metric_series(time_series):
    converted = time_series_to_numeric_series(time_series, ["p2"])
    assert len(converted.metric_names) == 1


def test_the_new_metric_name_carries_the_period_label(time_series):
    converted = time_series_to_numeric_series(time_series, ["p2"])
    assert converted.metric_names == ["Beds per 100k (2024/25)"]


def test_each_unit_keeps_its_value_for_the_selected_period(time_series):
    converted = time_series_to_numeric_series(time_series, ["p2"])
    values_by_unit = {u.unit_id: u.values[0] for u in converted.units}
    assert values_by_unit == {"u1": 11.0, "u2": 21.0, "u3": None}


def test_the_converted_shape_has_its_statistics_computed(time_series):
    """
    The result has to be a fully-formed NumericSeries, not a half-built one
    for someone else to finish.
    """
    converted = time_series_to_numeric_series(time_series, ["p1"])
    assert converted.metric_stats[0].count_with_data == 3
    assert converted.metric_stats[0].mean == 20.0


def test_two_selected_periods_become_two_metric_series(time_series):
    converted = time_series_to_numeric_series(time_series, ["p1", "p3"])
    assert converted.metric_names == [
        "Beds per 100k (2023/24)",
        "Beds per 100k (2025/26)",
    ]


# ---------------------------------------------------------------------------
# Chronological order wins over the order the ids were given in
# ---------------------------------------------------------------------------

def test_periods_come_out_in_the_shape_s_own_order_not_the_order_requested(time_series):
    """
    The user ticks checkboxes in whatever order they like. The chart must
    still read left to right in time.
    """
    converted = time_series_to_numeric_series(time_series, ["p3", "p1", "p2"])
    assert converted.metric_names == [
        "Beds per 100k (2023/24)",
        "Beds per 100k (2024/25)",
        "Beds per 100k (2025/26)",
    ]


def test_the_values_follow_the_reordered_columns(time_series):
    """
    Reordering the names without reordering the values would put the right
    labels on the wrong numbers, which is worse than an error.
    """
    converted = time_series_to_numeric_series(time_series, ["p3", "p1"])
    u1 = next(u for u in converted.units if u.unit_id == "u1")
    assert u1.values == [10.0, 12.0]      # 2023/24 then 2025/26


def test_a_repeated_period_id_produces_one_column_not_two(time_series):
    converted = time_series_to_numeric_series(time_series, ["p1", "p1"])
    assert converted.metric_names == ["Beds per 100k (2023/24)"]


# ---------------------------------------------------------------------------
# A period the shape does not have
# ---------------------------------------------------------------------------

def test_an_unknown_period_does_not_raise(time_series):
    """
    Documented as not an error. A Running Order row can legitimately name a
    period that a later data refresh no longer includes.
    """
    converted = time_series_to_numeric_series(time_series, ["nope"])
    assert converted is not None


def test_an_unknown_period_becomes_a_column_of_no_data(time_series):
    converted = time_series_to_numeric_series(time_series, ["nope"])
    assert converted.metric_names == ["Beds per 100k (nope)"]
    assert all(u.values == [None] for u in converted.units)


def test_an_unknown_period_is_labelled_with_the_bare_id(time_series):
    """There is no label to be had, so the id is shown rather than a blank."""
    converted = time_series_to_numeric_series(time_series, ["1338"])
    assert "1338" in converted.metric_names[0]


def test_unknown_periods_come_after_every_period_that_did_resolve(time_series):
    converted = time_series_to_numeric_series(time_series, ["nope", "p1"])
    assert converted.metric_names == [
        "Beds per 100k (2023/24)",
        "Beds per 100k (nope)",
    ]


# ---------------------------------------------------------------------------
# Several metric-series at once
# ---------------------------------------------------------------------------

def test_output_is_grouped_by_metric_series_then_by_period(make_time_series):
    """
    Metric-major, so the two periods of one metric sit together rather than
    interleaving with another metric's.
    """
    shape = make_time_series(
        periods=[("p1", "2024"), ("p2", "2025")],
        metrics={
            "Beds": {"u1": [1.0, 2.0]},
            "Staff": {"u1": [10.0, 20.0]},
        },
    )
    converted = time_series_to_numeric_series(shape, ["p1", "p2"])
    assert converted.metric_names == [
        "Beds (2024)", "Beds (2025)", "Staff (2024)", "Staff (2025)",
    ]


def test_a_unit_missing_from_one_metric_is_kept_with_no_data_for_it(make_time_series):
    """
    Documented: contributes None "rather than being dropped". u2 submitted
    Beds but not Staff, and must still appear on the Beds chart.
    """
    shape = make_time_series(
        periods=[("p1", "2024")],
        metrics={
            "Beds": {"u1": [1.0], "u2": [2.0]},
            "Staff": {"u1": [10.0]},
        },
    )
    converted = time_series_to_numeric_series(shape, ["p1"])
    u2 = next(u for u in converted.units if u.unit_id == "u2")
    assert u2.values == [2.0, None]


def test_the_unit_population_is_the_union_across_every_metric(make_time_series):
    shape = make_time_series(
        periods=[("p1", "2024")],
        metrics={
            "Beds": {"u1": [1.0]},
            "Staff": {"u2": [10.0]},
        },
    )
    converted = time_series_to_numeric_series(shape, ["p1"])
    assert [u.unit_id for u in converted.units] == ["u1", "u2"]


# ---------------------------------------------------------------------------
# What carries across, and what does not
# ---------------------------------------------------------------------------

def test_the_descriptive_fields_carry_across_unchanged(time_series):
    """
    population_table in particular: the next cut resolves its units from it,
    so losing it would break the population layers downstream.
    """
    converted = time_series_to_numeric_series(time_series, ["p1"])
    assert converted.title == time_series.title
    assert converted.population_table == time_series.population_table
    assert converted.format_modifier == time_series.format_modifier


def test_year_is_deliberately_left_empty(time_series):
    """
    A snapshot across several periods has no single year of its own, so
    inventing one would be a false statement on the chart.
    """
    assert time_series_to_numeric_series(time_series, ["p1", "p3"]).year is None


def test_the_shape_level_counts_describe_the_converted_shape(time_series):
    converted = time_series_to_numeric_series(time_series, ["p2"])
    assert converted.shape_stats.count_metric_series == 1
    assert converted.shape_stats.count_units == 3
    assert converted.shape_stats.count_units_with_any_data == 2   # u3 has a gap at p2


def test_converting_does_not_alter_the_time_series_it_came_from(time_series):
    before_periods = [p.period_id for p in time_series.periods]
    time_series_to_numeric_series(time_series, ["p1"])
    assert [p.period_id for p in time_series.periods] == before_periods
    assert len(time_series.metrics) == 1


# ---------------------------------------------------------------------------
# maybe_convert_periods_to_metrics: the no-op guard
# ---------------------------------------------------------------------------

def test_no_selected_periods_leaves_the_shape_exactly_as_it_was(time_series):
    """
    The common case: an insert_chart row with nothing in metric_periods.
    """
    assert maybe_convert_periods_to_metrics(time_series, []) is time_series


def test_a_non_timeseries_shape_is_left_alone_even_if_periods_are_named(numeric_series):
    """
    Documented as covering "a non-TimeSeries cache_file with a stray value
    in that column". It must not raise on data it cannot convert.
    """
    assert maybe_convert_periods_to_metrics(numeric_series, ["p1"]) is numeric_series


def test_a_timeseries_with_selected_periods_is_converted(time_series):
    converted = maybe_convert_periods_to_metrics(time_series, ["p1"])
    assert converted is not time_series
    assert converted.metric_names == ["Beds per 100k (2023/24)"]
