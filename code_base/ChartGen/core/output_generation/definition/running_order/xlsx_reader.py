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
        rows.append(row_dict)

    return rows
