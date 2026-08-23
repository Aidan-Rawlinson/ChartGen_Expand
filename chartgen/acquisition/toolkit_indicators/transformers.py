"""
transformers.py
Converts one Indicators toolkit report response into a TimeSeries data
shape. There is only one response shape here, so one transform function and
no dispatch table.

calculatedNationalAverages, dateAverages and dateMedians are all dropped.
Stats are recomputed locally per period from the raw per-unit values.

Every date in availableDates is kept, in the API's own order, trusted as
chronological and not re-sorted. No outputAvailability or visibility
filtering is applied: it would make a period's presence on the cached shape
depend on when Fetch happened to run.
"""

from chartgen.shared.normalisation_containers.shapes.timeseries import (
    TimeSeries, TimeSeriesPeriod, TimeSeriesMetric, TimeSeriesUnit,
    compute_time_series_period_stats,
)
from chartgen.shared.normalisation_containers.shapes.common import ShapeStats


def _optional_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def transform(report_details: dict, report_data: dict) -> "TimeSeries":
    """
    Build a TimeSeries shape (a single Metric-Series, per the current
    "one metric per fetch" API shape — the shape itself supports more, for
    whenever a fetch spans several).
    """
    kept_periods = report_data.get("availableDates", [])

    periods = [
        TimeSeriesPeriod(period_id=str(d["dateId"]), period_label=str(d.get("dateName", "")))
        for d in kept_periods
    ]

    # unit_id -> {unit_code, values: [None] * n_periods}
    units_by_id = {}
    n_periods = len(kept_periods)

    for i, period in enumerate(kept_periods):
        for org in period.get("organisationList", []):
            for sub in org.get("submissionData", []):
                sub_id = sub.get("submissionId")
                if sub_id is None:
                    continue
                sub_id = str(sub_id)
                entry = units_by_id.setdefault(sub_id, {
                    "unit_code": sub.get("anonSubmissionCode", ""),
                    "values": [None] * n_periods,
                })
                entry["values"][i] = _optional_float(sub.get("result"))

    units = [
        TimeSeriesUnit(unit_code=data["unit_code"], unit_id=uid, values=data["values"])
        for uid, data in units_by_id.items()
    ]

    period_stats = [
        compute_time_series_period_stats([u.values[i] for u in units])
        for i in range(n_periods)
    ]

    metric = TimeSeriesMetric(
        name=report_details.get("reportName"),
        units=units,
        period_stats=period_stats,
    )

    return TimeSeries(
        title=report_details.get("reportName"),
        format_modifier=report_details.get("formatModifier"),
        periods=periods,
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
