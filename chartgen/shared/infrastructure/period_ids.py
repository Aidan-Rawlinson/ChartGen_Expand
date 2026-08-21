"""
period_ids.py
Tiny, generic '^'-delimited period-id list <-> string helpers — no
Running-Order-specific knowledge, just a format. Lives in shared so
data-shape-normalisation code (chartgen.shared.normalisation_containers,
e.g. cut_resolution.py) can parse a metric_periods string without
depending on output_generation.definition (Architecture, Section 2 —
one-way dependencies: shared must not import from a higher layer).
chartgen.output_generation.definition.running_order.dialog_support re-exports
both for its existing callers.
"""

import re

_PERIOD_ID_PATTERN = re.compile(r"\(([^()]+)\)\s*$")


def parse_metric_periods_string(metric_periods_str: str) -> list:
    """Parse a '^'-delimited metric_periods string into a list of period_ids."""
    if not metric_periods_str:
        return []
    return [p.strip() for p in metric_periods_str.split("^") if p.strip()]


def build_metric_periods_string(period_ids: list) -> str:
    """Build a '^'-delimited metric_periods string from a list of period_ids, in the order given."""
    return "^".join(period_ids)


def extract_period_id(value) -> str:
    """
    Extract the bare period_id from a stored start_period/end_period
    value. The canonical stored form is whatever the person actually
    picked or typed — typically "period_label(period_id)" from a
    dropdown (e.g. "July 2025(1338)"), but a bare id typed by hand works
    identically. This extraction happens once, at the point a chart's cut
    is actually resolved for rendering — never at file read/write time,
    so the stored string itself is never rewritten or reconstructed (see
    running_order.schema's own note on why).

    Guards against one real environment fact, not a hypothetical: a bare
    id typed directly into an Excel cell may come back as a genuine
    numeric type rather than text (openpyxl reads it as a float), so a
    whole-number float is converted to a plain integer string first
    (str(1338.0) -> "1338", not "1338.0") before checking for a label.
    A blank value returns ''.
    """
    if isinstance(value, float) and value.is_integer():
        value = str(int(value))
    text = str(value or "").strip()
    if not text:
        return ""
    m = _PERIOD_ID_PATTERN.search(text)
    return m.group(1).strip() if m else text


def extract_metric_period_ids(value) -> str:
    """
    Extract a '^'-joined list of bare period_ids from a stored
    metric_periods value — one or more '^'-joined tokens, each in the
    same "label(id)" or bare-id form extract_period_id itself handles.
    Ready to hand straight to parse_metric_periods_string/prepare_chart_cut.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    return "^".join(extract_period_id(tok) for tok in text.split("^") if str(tok).strip())


def build_period_display(period_id: str, period_label: str = "") -> str:
    """
    Build the display string to store for a single picked period —
    "period_label(period_id)" when a label is known, the bare id alone
    otherwise (still valid; extract_period_id handles both forms
    identically). The inverse of extract_period_id. Blank period_id
    returns ''.
    """
    if not period_id:
        return ""
    return f"{period_label}({period_id})" if period_label else period_id


def extract_period_label(value) -> str:
    """
    Extract the label portion from a stored "period_label(period_id)"
    value — the inverse half of build_period_display/extract_period_id.
    Returns '' for a bare id with no label, or a blank value. Used only
    for display fallback (e.g. showing a previously-picked period's own
    label in a dropdown even when the current live shape no longer
    recognises that id) — never for anything that affects which data is
    actually resolved.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    m = _PERIOD_ID_PATTERN.search(text)
    return text[:m.start()].strip() if m else ""
