"""
reference_ids.py
Converts each shape type's own summary_stats() output into short, stable
id-tagged rows — {"id", "label", "kind", "value"} per stat — for display in
the Charts sheet and, eventually, as PowerPoint table replacement tags.

Ids are deliberately short (e.g. "Mn", "1Mna", "P2a") since they will be
used as literal PPT tags — a tag wider than the table cell it sits in
changes the table's own size, which is unacceptable. Scope is per
shape-type, not global: the same id (e.g. "{Mn}") means "Mean" in every
NumericSeries table, wherever that table template is reused, because every
NumericSeries shape has the identical fixed stat set. A CategoricalCompositional
or NumericCompositional shape's component count varies per metric-series, so
those ids include a running component number that isn't meaningful outside
that one metric-series' own table.

Series letter (a, b, c, ...) is appended only when a shape carries more than
one metric-series, and restarts at "a" every time — i.e. it identifies a
metric-series' position within *this* shape instance's own table set, not
a persistent identity across shapes. Omitted entirely for a single series,
by design (accepted trade-off: an id's meaning depends on current data
shape, not fixed at authoring time).

Period number (TimeSeries only) is prefixed ahead of the stat letter,
1-based in shape.periods order, so no two digits are ever adjacent (an id
component is always letter-bounded on both sides where two numbers would
otherwise collide, e.g. period 1 + component 1 cannot arise together since
TimeSeries carries no components).

"kind" on each row governs display/PPT formatting, not calculation:
  - "value"   — respects the shape's own format_modifier (£, %, plain)
  - "count"   — always a plain integer, regardless of format_modifier
  - "percent" — always shown as a %, independent of format_modifier
    (matches CategoricalCompositional's own chart-rendering convention —
    Functional Spec Section 10.2 — extended here to NumericCompositional's
    component-share figures for the same reason)
"""


def _series_letter(index: int) -> str:
    """0 -> 'a', 1 -> 'b', ..., 25 -> 'z', 26 -> 'aa', ... (Excel-column style)."""
    letters = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(97 + rem) + letters
    return letters


# Fixed stat set shared by NumericSeries and TimeSeries (per period, for the latter).
_FIXED_STAT_IDS = [
    ("n",              "C"),
    ("No data",        "Nd"),
    ("Mean",           "Mn"),
    ("Median",         "Md"),
    ("Lower Quartile", "Q1"),
    ("Upper Quartile", "Q3"),
    ("Min",            "Mi"),
    ("Max",            "Ma"),
]


def numeric_series_reference_rows(stats: dict) -> dict:
    """
    {metric_name: [{"id", "label", "kind", "value"}, ...]} from
    numeric_series_summary_stats() output. Series letter appended only if
    more than one metric-series is present.
    """
    multi = len(stats) > 1
    out = {}
    for i, (metric_name, metric_stats) in enumerate(stats.items()):
        letter = _series_letter(i) if multi else ""
        rows = []
        for label, id_prefix in _FIXED_STAT_IDS:
            kind = "count" if label in ("n", "No data") else "value"
            rows.append({
                "id": f"{id_prefix}{letter}", "label": label, "kind": kind,
                "value": metric_stats.get(label),
            })
        out[metric_name] = rows
    return out


def time_series_reference_rows(stats: dict) -> dict:
    """
    {metric_name: [{"id", "label", "kind", "value"}, ...]} from
    time_series_summary_stats() output — one row per (period, stat)
    combination. Period number (1-based, in shape.periods order) prefixes
    the stat letter; series letter appended only if more than one
    metric-series is present.
    """
    multi = len(stats) > 1
    out = {}
    for i, (metric_name, per_period) in enumerate(stats.items()):
        letter = _series_letter(i) if multi else ""
        rows = []
        for p_idx, (period_label, period_stats) in enumerate(per_period.items(), start=1):
            for label, id_prefix in _FIXED_STAT_IDS:
                kind = "count" if label in ("n", "No data") else "value"
                rows.append({
                    "id": f"{p_idx}{id_prefix}{letter}",
                    "label": f"{label} — {period_label}", "kind": kind,
                    "value": period_stats.get(label),
                })
        out[metric_name] = rows
    return out


def categorical_reference_rows(stats: dict) -> dict:
    """
    {question: [{"id", "label", "kind", "value"}, ...]} from
    categorical_summary_stats() output. Category count/id is 1-based,
    following category order; "P" + number is that category's percentage
    share. Series letter appended only if more than one question is present.
    """
    multi = len(stats) > 1
    out = {}
    for i, (question, q_stats) in enumerate(stats.items()):
        letter = _series_letter(i) if multi else ""
        rows = [
            {"id": f"C{letter}",  "label": "n",           "kind": "count", "value": q_stats.get("n")},
            {"id": f"Nr{letter}", "label": "No response",  "kind": "count", "value": q_stats.get("No response")},
        ]
        for c_idx, (cat_name, cat_stats) in enumerate(q_stats.get("Categories", {}).items(), start=1):
            rows.append({
                "id": f"{c_idx}{letter}", "label": f"{cat_name} — Count",
                "kind": "count", "value": cat_stats.get("Count"),
            })
            rows.append({
                "id": f"P{c_idx}{letter}", "label": f"{cat_name} — %",
                "kind": "percent", "value": cat_stats.get("%"),
            })
        out[question] = rows
    return out


def numeric_compositional_reference_rows(stats: dict) -> dict:
    """
    {metric_name: [{"id", "label", "kind", "value"}, ...]} from
    numeric_compositional_summary_stats() output. Component count/id is
    1-based, following component order; "P" + number is that component's
    share of the metric's total. Series letter appended only if more than
    one metric-series is present.
    """
    multi = len(stats) > 1
    out = {}
    for i, (metric_name, m_stats) in enumerate(stats.items()):
        letter = _series_letter(i) if multi else ""
        rows = [
            {"id": f"T{letter}", "label": "Total", "kind": "value", "value": m_stats.get("Total")},
        ]
        for c_idx, (comp_name, comp_stats) in enumerate(m_stats.get("Components", {}).items(), start=1):
            rows.append({
                "id": f"{c_idx}{letter}", "label": f"{comp_name} — Value",
                "kind": "value", "value": comp_stats.get("Value"),
            })
            rows.append({
                "id": f"P{c_idx}{letter}", "label": f"{comp_name} — %",
                "kind": "percent", "value": comp_stats.get("%"),
            })
        out[metric_name] = rows
    return out


# Keyed by the same shape_type strings already used across the Charts sheet
# and manifest (e.g. "NumericSeries", "TimeSeries") — see cache_reader/manifest
# shape_type column — so callers holding a shape_type string, not a shape
# instance, can dispatch without needing isinstance checks here.
REFERENCE_ROW_CONVERTERS = {
    "NumericSeries":           numeric_series_reference_rows,
    "NumericCompositional":    numeric_compositional_reference_rows,
    "CategoricalCompositional": categorical_reference_rows,
    "TimeSeries":              time_series_reference_rows,
}


def reference_rows_for_shape_type(shape_type: str, stats: dict) -> dict:
    """Dispatch to the correct reference-row converter for a known shape_type string."""
    convert = REFERENCE_ROW_CONVERTERS.get(shape_type)
    if convert is None:
        return {}
    return convert(stats)
