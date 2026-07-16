"""
transformers.py
Converts one Indicators toolkit report response into a TimeSeries data
shape. Unlike the NHS side (transformers.py, dispatched by storedProcedure
name across several report families), there is only one response shape
here — one transform function, no dispatch table needed.

calculatedNationalAverages is dropped entirely, per decision — never stored,
never computed. dateAverages/dateMedians are also dropped: stats are
recomputed locally per period from the raw per-unit values instead, the
same way every other shape computes stats against whatever population layer
gets resolved, just applied once per period rather than once for the whole
shape (see timeseries.py).

Only periods the project's own visible-dates list marks as visible
(outputAvailability <= today) are kept — mirroring the source VBA's own
filter exactly. availableDates' own order is trusted as chronological, not
re-sorted — same call the VBA makes (that order isn't guaranteed
documented behaviour, but the VBA has relied on it without issue).
"""

from datetime import date, datetime

from core.shared.normalisation_containers.shapes.timeseries import (
    TimeSeries, TimeSeriesPeriod, TimeSeriesMetric, TimeSeriesUnit,
    compute_time_series_period_stats,
)
from core.shared.normalisation_containers.shapes.common import ShapeStats


def _optional_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _visible_date_ids(project_dates: list) -> set:
    """Return the set of dateIds whose outputAvailability has already passed."""
    today = date.today()
    visible = set()
    for d in project_dates:
        avail = d.get("outputAvailability")
        if not avail:
            continue
        try:
            avail_date = datetime.fromisoformat(str(avail)[:10]).date()
        except ValueError:
            continue
        if avail_date <= today:
            visible.add(d.get("dateId"))
    return visible


def transform(report_details: dict, report_data: dict, project_dates: list) -> "TimeSeries":
    """
    Build a TimeSeries shape (a single Metric-Series, per the current
    "one metric per fetch" API shape — the shape itself supports more, for
    whenever a fetch spans several).
    """
    visible_ids = _visible_date_ids(project_dates)

    kept_periods = [
        d for d in report_data.get("availableDates", [])
        if d.get("dateId") in visible_ids
    ]

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
