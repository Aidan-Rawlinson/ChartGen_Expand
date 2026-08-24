"""
Tests for shared/normalisation_containers/shapes/numeric_series.py

These are the numbers that reach NHS-facing reports, so a silent error here
is the most damaging thing in the codebase. Nothing raises when a median is
wrong; it just gets printed.

Three things are pinned deliberately.

The percentile convention. compute_numeric_series_metric_stats uses linear
interpolation between the two neighbouring values, which is the same
convention as numpy's default and as Excel's PERCENTILE. It is not the only
reasonable choice: a nearest-rank convention would give different quartiles
on small populations, which is most benchmarking datasets. Swapping one for
the other would change published figures with no error anywhere, so the
expected values below are written out longhand rather than computed.

That None is not zero. A unit with no submission is counted in "No data",
excluded from the mean, and must never be averaged in as a nought.

That an empty population layer still produces one stats entry per named
metric-series. The docstring on _recalc_numeric_series_stats explains why:
otherwise "the layer's metric-series section" disappears from the report
entirely rather than showing as blank.
"""

from chartgen.shared.normalisation_containers.shapes import (
    NumericSeries,
    NumericSeriesUnit,
    compute_numeric_series_metric_stats,
    filter_numeric_series,
    numeric_series_summary_stats,
)
from chartgen.shared.normalisation_containers.shapes.numeric_series import (
    _percentile,
    _recalc_numeric_series_stats,
)


# ---------------------------------------------------------------------------
# _percentile: the convention, written out longhand
# ---------------------------------------------------------------------------

def test_the_median_of_an_odd_count_is_the_middle_value():
    assert _percentile([10.0, 20.0, 30.0], 50) == 20.0


def test_the_median_of_an_even_count_is_interpolated_between_the_middle_two():
    """
    Linear interpolation, so 2.5 rather than either neighbour. A nearest-rank
    convention would give 2.0 or 3.0 here.
    """
    assert _percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5


def test_the_lower_quartile_of_four_values_is_interpolated_not_snapped():
    """
    Q1 of [1,2,3,4] is 1.75 under linear interpolation. Under nearest-rank
    it would be 1.0 or 2.0. This is the single most consequential
    convention in the codebase, because quartiles are what benchmarking
    charts are built on.
    """
    assert _percentile([1.0, 2.0, 3.0, 4.0], 25) == 1.75


def test_the_upper_quartile_of_four_values_is_interpolated_not_snapped():
    assert _percentile([1.0, 2.0, 3.0, 4.0], 75) == 3.25


def test_a_single_value_is_its_own_percentile_at_every_point():
    for pct in [0, 25, 50, 75, 100]:
        assert _percentile([42.0], pct) == 42.0


def test_the_hundredth_percentile_is_the_maximum():
    assert _percentile([1.0, 2.0, 3.0], 100) == 3.0


# ---------------------------------------------------------------------------
# compute_numeric_series_metric_stats
# ---------------------------------------------------------------------------

def test_the_stats_of_a_simple_series_are_what_you_would_calculate_by_hand():
    stats = compute_numeric_series_metric_stats([1.0, 2.0, 3.0, 4.0])
    assert stats.count_with_data == 4
    assert stats.count_null == 0
    assert stats.mean == 2.5
    assert stats.median == 2.5
    assert stats.q1 == 1.75
    assert stats.q3 == 3.25
    assert stats.min == 1.0
    assert stats.max == 4.0


def test_units_with_no_data_are_counted_but_not_averaged_in():
    """
    The mean of [10, 20, None] is 15, not 10. Treating None as zero is the
    single easiest way to publish a wrong figure.
    """
    stats = compute_numeric_series_metric_stats([10.0, 20.0, None])
    assert stats.count_with_data == 2
    assert stats.count_null == 1
    assert stats.mean == 15.0


def test_a_zero_value_is_real_data_and_is_averaged_in():
    """
    The other half of the same rule. Zero is a submitted figure, not a gap.
    """
    stats = compute_numeric_series_metric_stats([0.0, 10.0])
    assert stats.count_with_data == 2
    assert stats.count_null == 0
    assert stats.mean == 5.0


def test_a_series_where_nobody_submitted_reports_no_data_rather_than_zeroes():
    """
    Every statistic is None, not 0.0. A chart showing a mean of zero for a
    metric nobody submitted would be a false statement.
    """
    stats = compute_numeric_series_metric_stats([None, None, None])
    assert stats.count_with_data == 0
    assert stats.count_null == 3
    assert stats.mean is None
    assert stats.median is None
    assert stats.min is None
    assert stats.max is None


def test_an_empty_series_reports_zero_units_and_no_statistics():
    stats = compute_numeric_series_metric_stats([])
    assert stats.count_with_data == 0
    assert stats.count_null == 0
    assert stats.mean is None


def test_values_are_sorted_before_the_quartiles_are_taken():
    """
    The input arrives in population-table order, not sorted order, so this
    is doing real work rather than restating the previous test.
    """
    unsorted = compute_numeric_series_metric_stats([4.0, 1.0, 3.0, 2.0])
    sorted_already = compute_numeric_series_metric_stats([1.0, 2.0, 3.0, 4.0])
    assert unsorted == sorted_already


def test_statistics_are_rounded_to_four_decimal_places():
    stats = compute_numeric_series_metric_stats([1.0, 2.0])
    assert stats.mean == 1.5
    thirds = compute_numeric_series_metric_stats([1.0, 1.0, 2.0])
    assert thirds.mean == 1.3333


def test_negative_values_are_handled_like_any_other_number():
    stats = compute_numeric_series_metric_stats([-10.0, 0.0, 10.0])
    assert stats.mean == 0.0
    assert stats.min == -10.0
    assert stats.max == 10.0


# ---------------------------------------------------------------------------
# Recalculation for a filtered population
# ---------------------------------------------------------------------------

def test_an_empty_population_still_gets_one_stats_entry_per_metric_series():
    """
    The documented rule. A peer group with no matching units still needs a
    stats block per named metric, so the layer shows as blank rather than
    vanishing from the report.
    """
    stats = _recalc_numeric_series_stats([], n_metrics=3)
    assert len(stats) == 3
    assert all(s.count_with_data == 0 for s in stats)


def test_each_metric_series_is_recalculated_independently():
    units = [
        NumericSeriesUnit(unit_code="A", unit_id="u1", values=[10.0, 100.0]),
        NumericSeriesUnit(unit_code="B", unit_id="u2", values=[20.0, 200.0]),
    ]
    stats = _recalc_numeric_series_stats(units, n_metrics=2)
    assert stats[0].mean == 15.0
    assert stats[1].mean == 150.0


# ---------------------------------------------------------------------------
# filter_numeric_series
# ---------------------------------------------------------------------------

def test_filtering_keeps_only_the_requested_units(make_numeric_series):
    shape = make_numeric_series({"u1": [10.0], "u2": [20.0], "u3": [30.0]})
    filtered = filter_numeric_series(shape, {"u1", "u3"})
    assert [u.unit_id for u in filtered.units] == ["u1", "u3"]


def test_filtering_recalculates_the_statistics_for_the_smaller_population(make_numeric_series):
    """
    The point of filtering. A peer group's mean must be the peer group's
    mean, not the whole population's carried over.
    """
    shape = make_numeric_series({"u1": [10.0], "u2": [20.0], "u3": [30.0]})
    assert shape.metric_stats[0].mean == 20.0

    filtered = filter_numeric_series(shape, {"u1", "u2"})
    assert filtered.metric_stats[0].mean == 15.0


def test_filtering_leaves_the_original_shape_untouched(make_numeric_series):
    """
    Layers are built by filtering the same shape repeatedly, so mutating it
    would make every layer after the first wrong.
    """
    shape = make_numeric_series({"u1": [10.0], "u2": [20.0], "u3": [30.0]})
    filter_numeric_series(shape, {"u1"})
    assert [u.unit_id for u in shape.units] == ["u1", "u2", "u3"]
    assert shape.metric_stats[0].mean == 20.0


def test_filtering_to_nobody_gives_an_empty_layer_rather_than_raising(make_numeric_series):
    shape = make_numeric_series({"u1": [10.0], "u2": [20.0]})
    filtered = filter_numeric_series(shape, set())
    assert filtered.units == []
    assert len(filtered.metric_stats) == 1
    assert filtered.metric_stats[0].count_with_data == 0


def test_filtering_records_how_many_units_actually_hold_data(make_numeric_series):
    """
    count_units and count_units_with_any_data are different facts, and a
    chart's "n" depends on telling them apart.
    """
    shape = make_numeric_series({"u1": [10.0], "u2": [None], "u3": [30.0]})
    filtered = filter_numeric_series(shape, {"u1", "u2", "u3"})
    assert filtered.shape_stats.count_units == 3
    assert filtered.shape_stats.count_units_with_any_data == 2


def test_filtering_carries_the_descriptive_fields_across(make_numeric_series):
    """
    A layer is still the same dataset. Losing population_table here would
    break the next cut's unit resolution.
    """
    shape = make_numeric_series({"u1": [10.0]}, population_table="submissions_2026")
    filtered = filter_numeric_series(shape, {"u1"})
    assert filtered.population_table == "submissions_2026"
    assert filtered.metric_names == shape.metric_names
    assert filtered.title == shape.title


# ---------------------------------------------------------------------------
# numeric_series_summary_stats
# ---------------------------------------------------------------------------

def test_summary_stats_are_keyed_by_metric_series_name(make_numeric_series):
    shape = make_numeric_series(
        {"u1": [10.0, 100.0], "u2": [20.0, 200.0]},
        metric_names=("Beds", "Staff"),
    )
    summary = numeric_series_summary_stats(shape)
    assert set(summary) == {"Beds", "Staff"}


def test_summary_stats_use_the_labels_the_report_displays(make_numeric_series):
    shape = make_numeric_series({"u1": [10.0], "u2": [20.0]})
    summary = numeric_series_summary_stats(shape)
    labels = set(next(iter(summary.values())))
    assert labels == {"n", "No data", "Min", "Lower Quartile", "Mean",
                      "Median", "Upper Quartile", "Max"}


def test_an_unnamed_metric_series_gets_a_positional_name():
    """
    Falls back rather than raising, so a shape built from an API response
    with a missing name still displays.
    """
    shape = NumericSeries(
        metric_names=[],
        units=[NumericSeriesUnit(unit_code="A", unit_id="u1", values=[1.0])],
        metric_stats=[compute_numeric_series_metric_stats([1.0])],
    )
    assert list(numeric_series_summary_stats(shape)) == ["Series 1"]
