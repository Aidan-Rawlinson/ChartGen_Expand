"""
conftest.py
Fixtures shared across the suite. pytest finds this automatically; no test
needs to import it.

Everything here builds invented data. There is no real submission data, no
real organisation names and no real workfile anywhere under tests/.
"""

import pytest

from chartgen.shared.normalisation_containers.shapes import (
    NumericSeries, NumericSeriesUnit, compute_numeric_series_metric_stats,
)


# ---------------------------------------------------------------------------
# Population tables
# ---------------------------------------------------------------------------

@pytest.fixture
def unit_rows():
    """
    Four units in one population table, with one peer-group column.

    "Region()" is a peer-group column (the "()" suffix is the convention,
    see peer_group_tokens.py). u4 has "x", which means "no group" and is
    treated identically to blank.
    """
    return [
        {"unit_id": "u1", "unit_code": "A01", "unit_name": "Alpha Trust",   "Region()": "North", "soft_parents": ""},
        {"unit_id": "u2", "unit_code": "B02", "unit_name": "Bravo Trust",   "Region()": "North", "soft_parents": ""},
        {"unit_id": "u3", "unit_code": "C03", "unit_name": "Charlie Trust", "Region()": "South", "soft_parents": ""},
        {"unit_id": "u4", "unit_code": "D04", "unit_name": "Delta Trust",   "Region()": "x",     "soft_parents": ""},
    ]


@pytest.fixture
def tables(unit_rows):
    """A workfile's tables dict with one table in it."""
    return {"submissions_2026": unit_rows}


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@pytest.fixture
def make_numeric_series():
    """
    Returns a function that builds a NumericSeries with its stats already
    computed, the way a real one arrives from a transformer.

    values_by_unit -- {unit_id: [value, ...]}, one value per metric name.
                      None means "no data for this unit", which is a
                      distinct case from zero throughout ChartGen.

    A factory rather than a ready-made shape, so one test can build several
    different populations and compare them.
    """
    def _build(values_by_unit, metric_names=("Beds per 100k",),
               population_table="submissions_2026", **kwargs):
        units = [
            NumericSeriesUnit(unit_id=uid, unit_code=uid.upper(), values=list(vals))
            for uid, vals in values_by_unit.items()
        ]
        metric_stats = [
            compute_numeric_series_metric_stats([u.values[m] for u in units])
            for m in range(len(metric_names))
        ]
        return NumericSeries(
            title="Invented test metric",
            metric_names=list(metric_names),
            population_table=population_table,
            units=units,
            metric_stats=metric_stats,
            **kwargs,
        )
    return _build


@pytest.fixture
def numeric_series(make_numeric_series):
    """One metric, four units, one of them with no data."""
    return make_numeric_series({
        "u1": [10.0],
        "u2": [20.0],
        "u3": [30.0],
        "u4": [None],
    })


# ---------------------------------------------------------------------------
# Running Order rows
# ---------------------------------------------------------------------------

@pytest.fixture
def running_order_rows():
    """
    A minimal but structurally realistic Running Order: the create_ppt
    header, two content rows, then the save_ppt/save_pdf footer.

    Only the columns a test actually reads are filled in. row_ops.py builds
    new rows from the full COLUMNS list itself, so a partial row here is
    enough and keeps the fixture readable.
    """
    return [
        {"row_id": 1, "enabled": 1, "scope": "normal", "function": "create_ppt",   "notes": "header"},
        {"row_id": 2, "enabled": 1, "scope": "normal", "function": "insert_chart", "notes": "first chart",
         "slide_index": "1", "base_chart_name": "ranked_column", "cache_file": "aa.json"},
        {"row_id": 3, "enabled": 1, "scope": "normal", "function": "insert_chart", "notes": "second chart",
         "slide_index": "2", "base_chart_name": "dot_strip", "cache_file": "bb.json"},
        {"row_id": 4, "enabled": 1, "scope": "normal", "function": "save_ppt",     "notes": "footer"},
        {"row_id": 5, "enabled": 1, "scope": "normal", "function": "save_pdf",     "notes": "footer"},
    ]


# ---------------------------------------------------------------------------
# TimeSeries, which carries a period axis the other shapes do not
# ---------------------------------------------------------------------------

@pytest.fixture
def make_time_series():
    """
    Returns a function that builds a TimeSeries.

    The period axis lives once on the shape, shared by every metric-series,
    and each unit's values list is parallel to it: same index, same order,
    None where that unit has no value for that period.

    periods -- [(period_id, period_label), ...] in chronological order.
    metrics -- {metric_name: {unit_id: [value per period]}}
    """
    from chartgen.shared.normalisation_containers.shapes import (
        TimeSeries, TimeSeriesMetric, TimeSeriesPeriod, TimeSeriesUnit,
    )

    def _build(periods, metrics, population_table="submissions_2026", **kwargs):
        return TimeSeries(
            title="Invented test time series",
            population_table=population_table,
            periods=[TimeSeriesPeriod(period_id=pid, period_label=label) for pid, label in periods],
            metrics=[
                TimeSeriesMetric(
                    name=name,
                    units=[
                        TimeSeriesUnit(unit_id=uid, unit_code=uid.upper(), values=list(vals))
                        for uid, vals in units.items()
                    ],
                )
                for name, units in metrics.items()
            ],
            **kwargs,
        )
    return _build


@pytest.fixture
def time_series(make_time_series):
    """One metric, three periods, three units, with one gap in the data."""
    return make_time_series(
        periods=[("p1", "2023/24"), ("p2", "2024/25"), ("p3", "2025/26")],
        metrics={"Beds per 100k": {
            "u1": [10.0, 11.0, 12.0],
            "u2": [20.0, 21.0, 22.0],
            "u3": [30.0, None, 32.0],
        }},
    )
