"""
period_ids.py
Generic '^'-delimited period-id list and string helpers. Format only, with
no Running Order knowledge.

running_order.dialog_support re-exports these, so a rename here has two
call sites.
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
    Extract the bare period_id from a stored start_period or end_period
    value. The stored form is whatever was picked or typed: typically
    "period_label(period_id)", or a bare id. Blank returns ''.

    A bare id typed into an Excel cell comes back from openpyxl as a float,
    so a whole-number float is converted to a plain integer string
    (1338.0 -> "1338", not "1338.0") before checking for a label.
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
