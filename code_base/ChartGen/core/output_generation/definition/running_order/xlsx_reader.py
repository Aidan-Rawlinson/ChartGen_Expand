"""
xlsx_reader.py
Reads a Running Order .xlsx back into row dicts.
"""

import re

from core.output_generation.definition.running_order.schema import COLUMNS, SCOPE_VALUES
from core.shared.infrastructure.constants import coerce_row

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

_PERIOD_ID_PATTERN = re.compile(r"\(([^()]+)\)\s*$")


def _extract_period_id(value) -> str:
    """
    Extract the trailing (period_id) from a written
    'period_label(period_id)' start_period/end_period cell — the canonical
    stored value is the id alone. A blank cell, or one that doesn't match
    the pattern (e.g. free text typed over the dropdown), returns '' rather
    than guessing at an id: an unresolved period_id already falls back to
    an empty period range at insert_chart time (same "unresolvable ->
    nothing" rule as an unresolvable population token), so there's no
    silent wrong-match risk either way.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    m = _PERIOD_ID_PATTERN.search(text)
    return m.group(1).strip() if m else ""


def _extract_metric_periods(value) -> str:
    """
    Parse a '^'-joined 'period_label(period_id)^period_label(period_id)...'
    metric_periods cell back into a '^'-joined list of ids. Each token is
    extracted independently via _extract_period_id — a malformed token
    (free text typed over what was a composite label) is dropped rather
    than guessed at, same leniency as a single start_period/end_period cell.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    ids = [_extract_period_id(tok) for tok in text.split("^")]
    return "^".join(i for i in ids if i)


def read_xlsx(path: str) -> list[dict]:
    """
    Read the Running Order .xlsx and return a list of row dicts.
    Skips the header row.
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required to read the Running Order xlsx.")

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    rows = []
    for excel_row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not any(v is not None for v in row):
            continue  # skip empty rows
        row_dict = {col: (row[i] if i < len(row) else "") for i, col in enumerate(COLUMNS)}
        row_dict.setdefault("enabled", "1")
        coerce_row(row_dict)
        # Normalise scope — default to "normal" if blank or missing
        scope = str(row_dict.get("scope", "")).strip()
        if scope not in SCOPE_VALUES:
            scope = "normal"
        row_dict["scope"] = scope
        row_dict["start_period"] = _extract_period_id(row_dict.get("start_period", ""))
        row_dict["end_period"] = _extract_period_id(row_dict.get("end_period", ""))
        row_dict["metric_periods"] = _extract_metric_periods(row_dict.get("metric_periods", ""))
        rows.append(row_dict)

    return rows
