"""
transformers.py
One transformation function per stored procedure group; each converts raw API JSON into a canonical data shape.

Metric-Series stats are not computed here — each shape module owns the single
canonical stats computation for its shape (compute_*_stats), shared with
population-filter recalculation.
"""

from core.shared.normalisation_containers.shapes import (
    NumericSeries, NumericSeriesUnit, ShapeStats,
    compute_numeric_series_metric_stats,
    NumericCompositional, NumericCompositionalMetric, NumericCompositionalUnit,
    compute_numeric_compositional_metric_stats,
    CategoricalCompositional, CategoricalCompositionalMetric,
    CategoricalCompositionalUnit,
    compute_categorical_metric_stats,
)


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
            unit_code=item.get("submissionCode") or "",
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
            unit_code=item.get("submissionCode") or "",
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
                unit_code=item.get("submissionCode") or "",
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
    yearData rows are segments (not units) — submissionCode is the segment label.
    response1 = sample average; response2 = unit value (null without a selected unit).
    has_valid_unit_data = False for this shape.
    """
    year_data = data.get("yearData", {}).get(year, [])

    segment_names = [item["submissionCode"] for item in year_data]
    sample_avg_values = [_optional_float(item.get("response1")) for item in year_data]
    count_with_data = sum(1 for v in sample_avg_values if v is not None)

    units = [NumericCompositionalUnit(
        unit_code="SAMPLE_AVG",
        unit_id="0",
        values=sample_avg_values,
    )]

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
        has_valid_unit_data=False,
        metrics=[metric],
        shape_stats=ShapeStats(
            count_metric_series=1,
            count_units=1,
            count_units_with_any_data=1 if count_with_data > 0 else 0,
        ),
    )


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
    "sp_a_generic_radar_to_dual_bar":                           transform_radar_chart,
}


def transform(raw_json: dict, year: str):
    """
    Dispatch entry point. Accepts the full API response dict and year string.
    Returns the appropriate canonical data shape, or raises if unrecognised.
    """
    data = raw_json["data"]
    proc = data["storedProcedure"]
    if proc not in PROCEDURE_MAP:
        raise ValueError(f"Unrecognised storedProcedure: {proc}")
    return PROCEDURE_MAP[proc](data, year)
