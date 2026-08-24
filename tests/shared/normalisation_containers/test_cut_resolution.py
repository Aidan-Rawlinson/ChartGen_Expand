"""
Tests for shared/normalisation_containers/cut_resolution.py

prepare_chart_cut is the shared middle of every chart path in ChartGen. Its
own docstring lists the callers: "insert_chart, the Charts sheet, Stat Tags,
the Chart Store and Output Tables". That is why it matters more than its size
suggests. The Charts sheet preview and the final report both go through here,
so if this drifts the preview stops predicting the report, and the user's
trust in the preview is the whole point of having one.

Three documented rules:

  "The bare id is extracted here and only here, so callers pass their stored
  value through unmodified and the stored string is never rewritten." This is
  the root CLAUDE.md rule about stored values, enforced at the one place it
  can be.

  "The range trim runs before the metric-periods conversion, so an id the
  trim has already cut out surfaces as not found rather than silently
  succeeding against the untrimmed shape."

  "Does not raise for a metric_periods id absent from the trimmed shape.
  That id's output metric carries no data for any unit."
"""

from chartgen.shared.normalisation_containers.cut_resolution import prepare_chart_cut


# ---------------------------------------------------------------------------
# No cut at all
# ---------------------------------------------------------------------------

def test_a_row_with_no_period_settings_passes_the_shape_straight_through(numeric_series, tables):
    shape, shape_type, target_rows, selected_ids = prepare_chart_cut(
        numeric_series, "NumericSeries", "", "", "",
        tables, ["submissions_2026"], {"submissions_2026": [{"unit_id": "u1"}]},
    )
    assert shape is numeric_series
    assert shape_type == "NumericSeries"


def test_the_target_rows_come_from_the_shape_s_own_population_table(numeric_series, tables):
    """
    Not from table_order[0]. A chart's units belong to the table its data
    came from, which may not be the master table.
    """
    _, _, target_rows, _ = prepare_chart_cut(
        numeric_series, "NumericSeries", "", "", "",
        tables, ["some_other_table"], {},
    )
    assert [r["unit_id"] for r in target_rows] == ["u1", "u2", "u3", "u4"]


def test_a_shape_with_no_recorded_population_table_falls_back_to_the_master_table(make_numeric_series, tables):
    """
    Documented fallback "only for cached data predating that field". Older
    workfiles still have to open.
    """
    shape = make_numeric_series({"u1": [1.0]}, population_table=None)
    _, _, target_rows, _ = prepare_chart_cut(
        shape, "NumericSeries", "", "", "",
        tables, ["submissions_2026"], {},
    )
    assert [r["unit_id"] for r in target_rows] == ["u1", "u2", "u3", "u4"]


def test_selected_ids_are_taken_from_the_full_unit_set_for_that_table(numeric_series, tables):
    full_unit_set = {"submissions_2026": [{"unit_id": "u2"}, {"unit_id": "u3"}]}
    _, _, _, selected_ids = prepare_chart_cut(
        numeric_series, "NumericSeries", "", "", "",
        tables, ["submissions_2026"], full_unit_set,
    )
    assert selected_ids == {"u2", "u3"}


def test_a_reporting_unit_absent_from_this_chart_s_table_selects_nobody(numeric_series, tables):
    """
    A legitimate case: the reporting unit did not submit to this project at
    all. It must resolve to an empty selection rather than raising.
    """
    _, _, _, selected_ids = prepare_chart_cut(
        numeric_series, "NumericSeries", "", "", "",
        tables, ["submissions_2026"], {"a_different_table": [{"unit_id": "u9"}]},
    )
    assert selected_ids == set()


# ---------------------------------------------------------------------------
# The stored value is passed through untouched
# ---------------------------------------------------------------------------

def test_a_stored_composite_period_string_is_understood(time_series, tables):
    """
    The caller hands over "2024/25(p2)" exactly as stored. Extraction
    happens here and nowhere else.
    """
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "2024/25(p2)", "", "",
        tables, ["submissions_2026"], {},
    )
    assert [p.period_id for p in shape.periods] == ["p2", "p3"]


def test_a_bare_stored_period_id_is_understood_too(time_series, tables):
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "p2", "", "",
        tables, ["submissions_2026"], {},
    )
    assert [p.period_id for p in shape.periods] == ["p2", "p3"]


def test_resolving_a_cut_does_not_rewrite_the_row_it_came_from(time_series, tables):
    """
    The values are passed by value, so this is really a check that nothing
    here reaches back. Stated as a test because the rule is absolute: "a
    value the user picked or typed stays exactly as they left it".
    """
    stored_start = "2024/25(p2)"
    prepare_chart_cut(
        time_series, "TimeSeries", stored_start, "", "",
        tables, ["submissions_2026"], {},
    )
    assert stored_start == "2024/25(p2)"


# ---------------------------------------------------------------------------
# The period-range trim
# ---------------------------------------------------------------------------

def test_a_start_period_trims_everything_before_it(time_series, tables):
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "p2", "", "", tables, ["submissions_2026"], {},
    )
    assert [p.period_id for p in shape.periods] == ["p2", "p3"]


def test_an_end_period_trims_everything_after_it(time_series, tables):
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "", "p2", "", tables, ["submissions_2026"], {},
    )
    assert [p.period_id for p in shape.periods] == ["p1", "p2"]


def test_a_start_and_an_end_keep_only_what_lies_between(time_series, tables):
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "p2", "p2", "", tables, ["submissions_2026"], {},
    )
    assert [p.period_id for p in shape.periods] == ["p2"]


# ---------------------------------------------------------------------------
# The metric-periods conversion
# ---------------------------------------------------------------------------

def test_selecting_metric_periods_reports_the_shape_as_numeric_series(time_series, tables):
    """
    effective_shape_type is what the chart-type dropdown filters on, so this
    is how a TimeSeries becomes eligible for a NumericSeries chart.
    """
    _, effective_type, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "", "", "p1^p2", tables, ["submissions_2026"], {},
    )
    assert effective_type == "NumericSeries"


def test_no_metric_periods_leaves_the_shape_type_alone(time_series, tables):
    _, effective_type, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "", "", "", tables, ["submissions_2026"], {},
    )
    assert effective_type == "TimeSeries"


def test_metric_periods_stored_with_labels_are_understood(time_series, tables):
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "", "", "2023/24(p1)^2025/26(p3)",
        tables, ["submissions_2026"], {},
    )
    assert shape.metric_names == [
        "Beds per 100k (2023/24)",
        "Beds per 100k (2025/26)",
    ]


# ---------------------------------------------------------------------------
# The trim runs before the conversion, and the order is load-bearing
# ---------------------------------------------------------------------------

def test_a_metric_period_cut_out_by_the_trim_is_treated_as_not_found(time_series, tables):
    """
    The documented reason the order matters. p1 has been trimmed away, so
    asking for it as a metric period must produce an empty column rather
    than quietly finding it on the untrimmed shape.
    """
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "p2", "", "p1", tables, ["submissions_2026"], {},
    )
    assert shape.metric_names == ["Beds per 100k (p1)"]      # bare id: not resolved
    assert all(u.values == [None] for u in shape.units)


def test_a_metric_period_inside_the_trim_resolves_normally(time_series, tables):
    """The other half of the same check, so the test above means something."""
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "p2", "", "p2", tables, ["submissions_2026"], {},
    )
    assert shape.metric_names == ["Beds per 100k (2024/25)"]


def test_an_unresolvable_metric_period_does_not_raise(time_series, tables):
    """
    Explicit in the docstring. A stale Running Order row must not stop the
    whole report; the chart shows the gap and the run continues.
    """
    shape, effective_type, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "", "", "no_such_period",
        tables, ["submissions_2026"], {},
    )
    assert effective_type == "NumericSeries"
    assert all(u.values == [None] for u in shape.units)


# ---------------------------------------------------------------------------
# The returned shape is the cut one
# ---------------------------------------------------------------------------

def test_the_returned_shape_reflects_the_cut_not_the_original(time_series, tables):
    """
    Documented for the callers that build their own fallback layer: "A
    caller building its own 'no populations resolved' fallback should use
    this, not the original, so the fallback reflects the same trims."
    """
    shape, _, _, _ = prepare_chart_cut(
        time_series, "TimeSeries", "p2", "p2", "", tables, ["submissions_2026"], {},
    )
    assert len(shape.periods) == 1
    assert len(time_series.periods) == 3
