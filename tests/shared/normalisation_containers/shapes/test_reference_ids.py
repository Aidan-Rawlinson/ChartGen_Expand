"""
Tests for shared/normalisation_containers/shapes/reference_ids.py

These ids become Stat Tags, which get typed into a PowerPoint template and
into Output Table cells and are replaced with a real figure at generation
time. So an id is a reference a human has written down somewhere else. If the
same id starts meaning a different statistic, every template already using it
silently prints the wrong number.

The module's own docstring flags the rule that makes this fragile:

  "A series letter (a, b, c, ...) is appended only when a shape carries more
  than one metric-series, and restarts at 'a' per shape instance. Omitted
  entirely for a single series, so an id's meaning depends on the shape's
  current series count rather than being fixed at authoring time."

That is a real sharp edge, not a bug: adding a second metric-series to a
dataset changes what "Mn" means. Worth pinning precisely so nobody
"fixes" it without realising what it would break.

Also: "Ids must stay short, because they are used as literal PowerPoint tags
and a tag wider than its cell changes the table's size."
"""

from chartgen.shared.normalisation_containers.shapes.reference_ids import (
    REFERENCE_ROW_CONVERTERS,
    _series_letter,
    categorical_reference_rows,
    numeric_compositional_reference_rows,
    numeric_series_reference_rows,
    reference_rows_for_shape_type,
    time_series_reference_rows,
)

ONE_SERIES = {"Beds": {"n": 3, "No data": 1, "Mean": 20.0, "Median": 20.0,
                       "Lower Quartile": 15.0, "Upper Quartile": 25.0,
                       "Min": 10.0, "Max": 30.0}}

TWO_SERIES = {
    "Beds":  dict(ONE_SERIES["Beds"]),
    "Staff": {"n": 2, "No data": 0, "Mean": 5.0, "Median": 5.0,
              "Lower Quartile": 4.0, "Upper Quartile": 6.0, "Min": 4.0, "Max": 6.0},
}


def ids_for(rows_by_metric, metric_name):
    return [row["id"] for row in rows_by_metric[metric_name]]


# ---------------------------------------------------------------------------
# The series letter
# ---------------------------------------------------------------------------

def test_series_letters_run_through_the_alphabet():
    assert _series_letter(0) == "a"
    assert _series_letter(1) == "b"
    assert _series_letter(25) == "z"


def test_series_letters_carry_over_like_spreadsheet_columns():
    assert _series_letter(26) == "aa"


# ---------------------------------------------------------------------------
# NumericSeries
# ---------------------------------------------------------------------------

def test_a_single_series_shape_has_no_series_letter_on_its_ids():
    assert ids_for(numeric_series_reference_rows(ONE_SERIES), "Beds") == [
        "C", "Nd", "Mn", "Md", "Q1", "Q3", "Mi", "Ma",
    ]


def test_a_two_series_shape_appends_a_letter_to_every_id():
    rows = numeric_series_reference_rows(TWO_SERIES)
    assert ids_for(rows, "Beds") == ["Ca", "Nda", "Mna", "Mda", "Q1a", "Q3a", "Mia", "Maa"]
    assert ids_for(rows, "Staff") == ["Cb", "Ndb", "Mnb", "Mdb", "Q1b", "Q3b", "Mib", "Mab"]


def test_adding_a_second_series_changes_what_an_id_means():
    """
    Recording the documented sharp edge rather than endorsing it. "Mn" is
    the mean on a one-series shape; on a two-series shape the mean is "Mna"
    and "Mn" refers to nothing. A Stat Tag written against the first would
    stop resolving.
    """
    one = ids_for(numeric_series_reference_rows(ONE_SERIES), "Beds")
    two = ids_for(numeric_series_reference_rows(TWO_SERIES), "Beds")
    assert "Mn" in one
    assert "Mn" not in two
    assert "Mna" in two


def test_the_series_letter_restarts_at_a_for_each_shape():
    """
    Scope is per shape instance, not global, so two different charts each
    start from "a".
    """
    for _ in range(2):
        rows = numeric_series_reference_rows(TWO_SERIES)
        assert ids_for(rows, "Beds")[0] == "Ca"


def test_counts_are_marked_as_counts_and_the_rest_as_values():
    """
    "kind" governs display formatting, not calculation. A count formatted
    with the shape's currency modifier would print "£3 units".
    """
    rows = numeric_series_reference_rows(ONE_SERIES)["Beds"]
    kinds = {row["label"]: row["kind"] for row in rows}
    assert kinds["n"] == "count"
    assert kinds["No data"] == "count"
    assert kinds["Mean"] == "value"
    assert kinds["Median"] == "value"


def test_each_row_carries_the_statistic_s_actual_value():
    rows = numeric_series_reference_rows(ONE_SERIES)["Beds"]
    by_label = {row["label"]: row["value"] for row in rows}
    assert by_label["Mean"] == 20.0
    assert by_label["n"] == 3


def test_a_missing_statistic_comes_through_as_no_value_rather_than_raising():
    """
    An empty population layer has None for every statistic, and its
    reference rows still have to exist so the table can show blanks.
    """
    rows = numeric_series_reference_rows({"Beds": {}})["Beds"]
    assert all(row["value"] is None for row in rows)
    assert len(rows) == 8


def test_every_row_has_the_four_fields_a_stat_tag_needs():
    for row in numeric_series_reference_rows(ONE_SERIES)["Beds"]:
        assert set(row) == {"id", "label", "kind", "value"}


def test_ids_stay_short_enough_to_sit_in_a_table_cell():
    """
    Documented constraint: these are literal PowerPoint tags, and a tag
    wider than its cell changes the table's size.
    """
    for rows in numeric_series_reference_rows(TWO_SERIES).values():
        for row in rows:
            assert len(row["id"]) <= 4, row["id"]


# ---------------------------------------------------------------------------
# TimeSeries: a period number in front of the stat letter
# ---------------------------------------------------------------------------

def test_time_series_ids_carry_a_one_based_period_number():
    stats = {"Beds": {
        "2024": {"n": 2, "Mean": 10.0},
        "2025": {"n": 2, "Mean": 20.0},
    }}
    ids = ids_for(time_series_reference_rows(stats), "Beds")
    assert "1Mn" in ids
    assert "2Mn" in ids


def test_time_series_rows_are_grouped_by_statistic_not_by_period():
    """
    Documented: "grouped by stat type first, so every period's Mean sits
    together". Row order is what a user reads down in the Charts sheet.
    """
    stats = {"Beds": {"2024": {"n": 1, "Mean": 10.0}, "2025": {"n": 1, "Mean": 20.0}}}
    ids = ids_for(time_series_reference_rows(stats), "Beds")
    assert ids[:2] == ["1C", "2C"]        # both periods' n, together
    assert ids[4:6] == ["1Mn", "2Mn"]     # both periods' Mean, together


def test_a_time_series_label_names_the_period_it_belongs_to():
    stats = {"Beds": {"2024/25": {"Mean": 10.0}}}
    rows = time_series_reference_rows(stats)["Beds"]
    mean_row = next(r for r in rows if r["id"] == "1Mn")
    assert "2024/25" in mean_row["label"]


# ---------------------------------------------------------------------------
# Compositional shapes: a running component number
# ---------------------------------------------------------------------------

def test_component_ids_are_numbered_from_one_in_component_order():
    stats = {"Spend": {"Total": 100.0, "Components": {
        "Staff": {"Value": 60.0, "%": 60.0},
        "Drugs": {"Value": 40.0, "%": 40.0},
    }}}
    ids = ids_for(numeric_compositional_reference_rows(stats), "Spend")
    assert ids == ["T", "1", "P1", "2", "P2"]


def test_a_component_percentage_is_always_formatted_as_a_percentage():
    """
    Even on a shape whose format_modifier is currency: a component's share
    is a share, not an amount.
    """
    stats = {"Spend": {"Total": 100.0, "Components": {"Staff": {"Value": 60.0, "%": 60.0}}}}
    rows = numeric_compositional_reference_rows(stats)["Spend"]
    percent_row = next(r for r in rows if r["id"] == "P1")
    assert percent_row["kind"] == "percent"


def test_categorical_ids_cover_the_response_counts_and_the_shares():
    stats = {"Q1": {"n": 10, "No response": 2, "Categories": {
        "Yes": {"Count": 6, "%": 60.0},
        "No":  {"Count": 4, "%": 40.0},
    }}}
    ids = ids_for(categorical_reference_rows(stats), "Q1")
    assert ids == ["C", "Nr", "1", "P1", "2", "P2"]


def test_a_compositional_shape_with_no_components_still_reports_its_total():
    """
    An empty population layer, which must still produce a row rather than
    an empty list.
    """
    rows = numeric_compositional_reference_rows({"Spend": {"Total": None}})["Spend"]
    assert [r["id"] for r in rows] == ["T"]


# ---------------------------------------------------------------------------
# Dispatch by shape_type string
# ---------------------------------------------------------------------------

def test_each_shape_type_dispatches_to_its_own_converter():
    assert reference_rows_for_shape_type("NumericSeries", ONE_SERIES) == \
        numeric_series_reference_rows(ONE_SERIES)


def test_an_unknown_shape_type_gives_nothing_rather_than_raising():
    assert reference_rows_for_shape_type("NotAShape", ONE_SERIES) == {}


def test_paired_survey_data_has_no_converter_and_so_no_stat_tags():
    """
    Documented in shapes/__init__.py: "PairedSurveyData has no
    REFERENCE_ROW_CONVERTERS entry, so it does not participate in Stat
    Tags." Deliberate, and it must not raise when asked.
    """
    assert "PairedSurveyData" not in REFERENCE_ROW_CONVERTERS
    assert reference_rows_for_shape_type("PairedSurveyData", {}) == {}


def test_the_four_participating_shape_types_are_all_wired_up():
    assert set(REFERENCE_ROW_CONVERTERS) == {
        "NumericSeries", "NumericCompositional", "CategoricalCompositional", "TimeSeries",
    }
