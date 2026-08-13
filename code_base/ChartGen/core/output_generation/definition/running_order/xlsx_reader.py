"""
xlsx_reader.py
Reads a Running Order .xlsx back into row dicts.
"""

from core.output_generation.definition.running_order.schema import COLUMNS, SCOPE_VALUES
from core.shared.infrastructure.constants import coerce_row

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def _period_cell_to_str(value) -> str:
    """
    A start_period/end_period/metric_periods cell's value, read back
    exactly as stored -- whatever the person picked or typed, typically
    "period_label(period_id)" (e.g. "July 2025(1338)") from a dropdown
    pick, or a bare id typed by hand. No parsing, no extraction happens
    here; the numeric id is pulled back out only where a chart's cut is
    actually resolved (core.shared.infrastructure.period_ids.
    extract_period_id/extract_metric_period_ids, via
    cut_resolution.prepare_chart_cut) — never at file read time, so this
    stored string is never rewritten.

    Guards against one real environment fact, not a hypothetical: a bare
    id typed directly into one of these cells may come back from Excel as
    a genuine numeric type rather than text. str(1338.0) gives "1338.0",
    not "1338" — a real mismatch against the plain string ids extraction
    later expects. A whole-number float is rendered without its trailing
    ".0"; anything else (blank, already a string, a genuinely fractional
    number) is just str()'d and stripped.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value or "").strip()


def _restore_json_suffix(value) -> str:
    """
    Add back the ".json" suffix xlsx_writer.py strips from the cache_file
    cell on export -- the actual cache dict key needs it, but the user
    types/pastes the bare hex id. A blank cell or the literal "none" stays
    as-is; a value already ending ".json" (an old export, or typed in full
    by hand) is left untouched rather than double-suffixed.
    """
    text = str(value or "").strip()
    if not text or text.lower() == "none":
        return text
    if text.lower().endswith(".json"):
        return text
    return f"{text}.json"


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
        row_dict["start_period"] = _period_cell_to_str(row_dict.get("start_period", ""))
        row_dict["end_period"] = _period_cell_to_str(row_dict.get("end_period", ""))
        row_dict["metric_periods"] = _period_cell_to_str(row_dict.get("metric_periods", ""))
        row_dict["cache_file"] = _restore_json_suffix(row_dict.get("cache_file", ""))
        rows.append(row_dict)

    return rows
