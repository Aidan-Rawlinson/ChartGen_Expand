"""
transformers.py
One transformation function per stored procedure group; each converts raw API JSON into a canonical data shape.

Metric-Series stats are not computed here. Each shape module owns the single
canonical stats computation for its shape.
"""

from dataclasses import replace

from chartgen.shared.normalisation_containers.shapes import (
    NumericSeries, NumericSeriesUnit, ShapeStats,
    compute_numeric_series_metric_stats,
    NumericCompositional, NumericCompositionalMetric, NumericCompositionalUnit,
    compute_numeric_compositional_metric_stats,
    CategoricalCompositional, CategoricalCompositionalMetric,
    CategoricalCompositionalUnit,
    compute_categorical_metric_stats,
)
from .submission_codes import normalise_submission_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _optional_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _unit_id_str(value) -> str:
    """Coerce a raw API unit/submission id to the canonical string form."""
    return str(value) if value is not None else "0"


# ---------------------------------------------------------------------------
# sp_a_generic_bar_chart_* → NumericSeries
# ---------------------------------------------------------------------------

def transform_bar_chart(data, year):
    """
    Single and multi-response bar charts.
    Each response field (response1, response2, ...) is one Metric-Series.
    """
    year_data = data.get("yearData", {}).get(year, [])

    # Count response fields from first row
    n_metrics = 0
    if year_data:
        i = 1
        while f"response{i}" in year_data[0]:
            n_metrics += 1
            i += 1

    # Metric names from reportParameters if available
    report_params = data.get("reportParameters", {})
    if report_params:
        sorted_params = sorted(report_params.values(), key=lambda x: x.get("displaySequence", 0))
        metric_names = [p.get("seriesName", f"Series {i+1}") for i, p in enumerate(sorted_params)]
    else:
        metric_names = [f"Series {i+1}" for i in range(n_metrics)]
    metric_names = metric_names[:n_metrics]

    units = []
    for item in year_data:
        values = [_optional_float(item.get(f"response{i+1}")) for i in range(n_metrics)]
        units.append(NumericSeriesUnit(
            unit_code=normalise_submission_code(item.get("submissionCode")),
            unit_id=_unit_id_str(item.get("submissionId")),
            values=values,
        ))

    metric_stats = [
        compute_numeric_series_metric_stats([u.values[i] for u in units])
        for i in range(n_metrics)
    ]

    return NumericSeries(
        title=data.get("reportName"),
        metric_names=metric_names,
        year=int(year),
        format_modifier=data.get("formatModifier"),
        has_valid_unit_data=True,
        units=units,
        shape_stats=ShapeStats(
            count_metric_series=n_metrics,
            count_units=len(units),
            count_units_with_any_data=sum(
                1 for u in units if any(v is not None for v in u.values)
            ),
        ),
        metric_stats=metric_stats,
    )


# ---------------------------------------------------------------------------
# sp_a_generic_list_pie_chart_* → CategoricalCompositional
# ---------------------------------------------------------------------------

def transform_pie_chart(data, year):
    """
    One Metric-Series; categories are pie segments.
    yearData: population-level percentages per category.
    tableData: per-unit responses.
    """
    year_data = data.get("yearData", {}).get(year, [])
    table_data = data.get("tableData", {}).get(year, [])

    category_names = [item["itemName"] for item in year_data]

    units = [
        CategoricalCompositionalUnit(
            unit_code=normalise_submission_code(item.get("submissionCode")),
            unit_id=_unit_id_str(item.get("submissionId")),
            response=item.get("response"),
        )
        for item in table_data
    ]

    stats = compute_categorical_metric_stats(units, category_names)

    metric = CategoricalCompositionalMetric(
        name=data.get("reportName"),
        category_names=category_names,
        units=units,
        stats=stats,
    )

    return CategoricalCompositional(
        title=data.get("reportName"),
        year=int(year),
        format_modifier=data.get("formatModifier"),
        has_valid_unit_data=True,
        metrics=[metric],
        shape_stats=ShapeStats(
            count_metric_series=1,
            count_units=len(units),
            count_units_with_any_data=stats.count_with_data,
        ),
    )


# ---------------------------------------------------------------------------
# sp_a_generic_yn_chart_* → CategoricalCompositional
# ---------------------------------------------------------------------------

def transform_yn_chart(data, year):
    """
    Multiple Metric-Series — one per question.
    yearData: population-level yes/no percentages per question.
    tableData: per-unit responses, one row per unit per question.
    """
    year_data = data.get("yearData", {}).get(year, [])
    table_data = data.get("tableData", {}).get(year, [])

    questions = [item["metric"] for item in year_data]
    category_names = ["Yes", "No"]

    # Group tableData rows by question
    by_question = {q: [] for q in questions}
    for item in table_data:
        q = item.get("seriesName")
        if q in by_question:
            by_question[q].append(item)

    metrics = []
    for question in questions:
        units = []
        for item in by_question.get(question, []):
            raw = item.get("response")
            response = raw if raw not in (None, "-", " ") else None
            units.append(CategoricalCompositionalUnit(
                unit_code=normalise_submission_code(item.get("submissionCode")),
                unit_id=_unit_id_str(item.get("submissionId")),
                response=response,
            ))
        metrics.append(CategoricalCompositionalMetric(
            name=question,
            category_names=category_names,
            units=units,
            stats=compute_categorical_metric_stats(units, category_names),
        ))

    all_ids = {u.unit_id for m in metrics for u in m.units}
    ids_with_data = {u.unit_id for m in metrics for u in m.units if u.response is not None}

    return CategoricalCompositional(
        title=data.get("reportName"),
        year=int(year),
        format_modifier=data.get("formatModifier"),
        has_valid_unit_data=True,
        metrics=metrics,
        shape_stats=ShapeStats(
            count_metric_series=len(metrics),
            count_units=len(all_ids),
            count_units_with_any_data=len(ids_with_data),
        ),
    )


# ---------------------------------------------------------------------------
# sp_a_generic_radar_* → NumericCompositional (partial)
# ---------------------------------------------------------------------------

def transform_radar_chart(data, year):
    """
    Radar/skill mix chart.

    yearData rows are population-level segment stats (segmentName,
    averageValue) — not units, and carry no per-submission fields at all.

    tableData rows are already full per-submission data: one row per real
    submission, with response1..responseN values, each paired with a
    response{i}Name giving the segment it belongs to. One row per report
    represents the network's own aggregate (submissionCode is null there,
    not a real submitting unit) and is excluded.
    """
    year_data = data.get("yearData", {}).get(year, [])
    table_data = data.get("tableData", {}).get(year, [])

    n_segments = 0
    if table_data:
        i = 1
        while f"response{i}" in table_data[0]:
            n_segments += 1
            i += 1
        segment_names = [table_data[0].get(f"response{i+1}Name") for i in range(n_segments)]
    else:
        segment_names = [item.get("segmentName") for item in year_data]

    units = []
    for item in table_data:
        code = item.get("submissionCode")
        if code is None:
            # Network-level aggregate row, not a real submitting unit.
            continue
        values = [_optional_float(item.get(f"response{i+1}")) for i in range(n_segments)]
        units.append(NumericCompositionalUnit(
            unit_code=normalise_submission_code(code),
            unit_id=_unit_id_str(item.get("submissionId")),
            values=values,
        ))

    metric = NumericCompositionalMetric(
        name=data.get("reportName"),
        component_names=segment_names,
        units=units,
        stats=compute_numeric_compositional_metric_stats(units),
    )

    return NumericCompositional(
        title=data.get("reportName"),
        year=int(year),
        format_modifier=data.get("formatModifier"),
        has_valid_unit_data=True,
        metrics=[metric],
        shape_stats=ShapeStats(
            count_metric_series=1,
            count_units=len(units),
            count_units_with_any_data=sum(
                1 for u in units if any(v is not None for v in u.values)
            ),
        ),
    )


# ---------------------------------------------------------------------------
# sp_a_generic_radar_to_dual_bar → NumericCompositional (per-unit via cycling)
# ---------------------------------------------------------------------------

def transform_radar_to_dual_bar(data, year, per_unit_responses=None):
    """
    "Radar to dual bar" chart. Unlike sp_a_generic_radar_chart, this
    procedure never returns per-submission data in a single call:
    tableData is always empty ({}), and yearData rows are one per
    segment/category (population-level only) — confusingly, the segment
    label is carried in a field still called submissionCode, not a real
    submission code. response1 is the sample average; response2 is null
    unless a specific organisation_id is passed to the call, in which case
    it becomes that organisation's own value.

    per_unit_responses, when supplied, is a list of (unit_code, unit_id,
    values) tuples built by cycling get_chart_data once per organisation
    and reading each call's response2 per segment (see fetch.py's cycling
    helper). When present, these become the shape's real per-unit data and
    has_valid_unit_data is True. When absent (e.g. no submissions table
    available yet), falls back to a single synthetic SAMPLE_AVG unit,
    has_valid_unit_data False.
    """
    year_data = data.get("yearData", {}).get(year, [])

    segment_names = [item.get("submissionCode") for item in year_data]
    sample_avg_values = [_optional_float(item.get("response1")) for item in year_data]

    if per_unit_responses:
        units = [
            NumericCompositionalUnit(unit_code=code, unit_id=uid, values=values)
            for code, uid, values in per_unit_responses
        ]
        has_valid_unit_data = True
    else:
        units = [NumericCompositionalUnit(
            unit_code="SAMPLE_AVG",
            unit_id="0",
            values=sample_avg_values,
        )]
        has_valid_unit_data = False

    metric = NumericCompositionalMetric(
        name=data.get("reportName"),
        component_names=segment_names,
        units=units,
        stats=compute_numeric_compositional_metric_stats(units),
    )

    return NumericCompositional(
        title=data.get("reportName"),
        year=int(year),
        format_modifier=data.get("formatModifier"),
        has_valid_unit_data=has_valid_unit_data,
        metrics=[metric],
        shape_stats=ShapeStats(
            count_metric_series=1,
            count_units=len(units),
            count_units_with_any_data=sum(
                1 for u in units if any(v is not None for v in u.values)
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Title placeholder resolution
# ---------------------------------------------------------------------------

def _resolve_title(report_name, year, option, data):
    """
    Replace NHS toolkit title placeholders with real values.

    report_name may contain literal `*` wildcard markers (stripped, as they
    foul the replacements below) and any of the year tokens or
    `|OPTION_TITLE|`. `option` is the 0-indexed denominatorOptionId parsed
    from the chart's URL; charts with no denominator options simply won't
    carry the `|OPTION_TITLE|` token in their reportName, so the lookup
    below is only attempted when the token is present.
    """
    if not report_name:
        return report_name

    title = report_name.replace("*", "")
    year_int = int(year)

    replacements = {
        "|DOUBLE_YEAR_CURRENT|":  str(year_int),
        "|DOUBLE_YEAR_PREVIOUS|": str(year_int - 1),
        "|DOUBLE_YEAR_MINUS_2|":  str(year_int - 2),
        "|DOUBLE_YEAR_NEXT|":     str(year_int + 1),
        "|SINGLE_YEAR_CURRENT|":  str(year_int)[-2:],
        "|SINGLE_YEAR_PREVIOUS|": str(year_int - 1)[-2:],
        "|SINGLE_YEAR_MINUS_2|":  str(year_int - 2)[-2:],
        "|SINGLE_YEAR_MINUS_3|":  str(year_int - 3)[-2:],
        "|SINGLE_YEAR_NEXT|":     str(year_int + 1)[-2:],
    }

    if "|OPTION_TITLE|" in title:
        denominators = (data.get("options") or {}).get("denominators") or []
        option_title = ""
        if 0 <= option < len(denominators):
            option_title = str(denominators[option].get("titleOptionName") or "").strip()
        replacements["|OPTION_TITLE|"] = option_title

    for token, value in replacements.items():
        title = title.replace(token, value)

    return title


# ---------------------------------------------------------------------------
# Dispatch map and entry point
# ---------------------------------------------------------------------------

PROCEDURE_MAP = {
    "sp_a_generic_bar_chart_parameter_controls":                transform_bar_chart,
    "sp_a_generic_bar_chart_full_response":                     transform_bar_chart,
    "sp_a_generic_difference_bar_chart":                        transform_bar_chart,
    "sp_a_generic_dual_bar_chart":                              transform_bar_chart,
    "sp_a_generic_dual_bar_chart_full_response":                transform_bar_chart,
    "sp_a_generic_stacked_bar_chart":                           transform_bar_chart,
    "sp_a_generic_multiple_dual_bar":                           transform_bar_chart,
    "sp_a_generic_dual_bar_chart_full_response_alt_sort_order": transform_bar_chart,
    "sp_a_generic_multiple_dual_bar_alt_sort_order":            transform_bar_chart,
    "sp_a_generic_yn_chart_exclude_na":                         transform_yn_chart,
    "sp_a_generic_yn_chart":                                    transform_yn_chart,
    "sp_a_generic_national_avg_sb_chart_alt":                   transform_yn_chart,
    "sp_a_generic_list_pie_chart":                              transform_pie_chart,
    "sp_a_generic_list_pie_chart_exclude_na":                   transform_pie_chart,
    "sp_a_generic_radar_chart":                                 transform_radar_chart,
    "sp_a_generic_radar_to_dual_bar":                           transform_radar_to_dual_bar,
}

# Procedures with no per-submission data in a single call — fetch.py cycles
# get_chart_data once per organisation for these and passes the results in
# as transform()'s per_unit_responses. Every other procedure ignores it.
CYCLE_PROCS = {"sp_a_generic_radar_to_dual_bar"}


def transform(raw_json: dict, year: str, option: int = 0, per_unit_responses=None):
    """
    Dispatch entry point. Accepts the full API response dict, year string,
    and the 0-indexed denominatorOptionId parsed from the chart's URL
    (defaults to 0 — the same default url_parser.py uses when a chart's URL
    carries no `option` param). Returns the appropriate canonical data
    shape, or raises if unrecognised.

    per_unit_responses is only meaningful for CYCLE_PROCS (see
    transform_radar_to_dual_bar) and is ignored for every other procedure.

    Title placeholder resolution (year tokens, `|OPTION_TITLE|`, and
    wildcard `*` stripping) is applied once here, after shape construction,
    rather than duplicated across each per-procedure transformer.
    """
    data = raw_json["data"]
    proc = data["storedProcedure"]
    if proc not in PROCEDURE_MAP:
        raise ValueError(f"Unrecognised storedProcedure: {proc}")
    if proc in CYCLE_PROCS:
        shape = transform_radar_to_dual_bar(data, year, per_unit_responses=per_unit_responses)
    else:
        shape = PROCEDURE_MAP[proc](data, year)
    resolved_title = _resolve_title(data.get("reportName"), year, option, data)
    shape = replace(shape, title=resolved_title)

    # Pie charts duplicate the raw title into their single metric's `name`
    # (drawn directly onto the chart by dot_matrix.py) — reuse the title
    # already resolved above rather than resolving it a second time.
    if proc in ("sp_a_generic_list_pie_chart", "sp_a_generic_list_pie_chart_exclude_na"):
        updated_metric = replace(shape.metrics[0], name=resolved_title)
        shape = replace(shape, metrics=[updated_metric])

    return shape
