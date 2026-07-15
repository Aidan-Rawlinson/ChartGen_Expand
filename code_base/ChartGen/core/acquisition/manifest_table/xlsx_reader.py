"""
xlsx_reader.py
Reads an edited manifest .xlsx back and applies it to WorkfileState's
manifest table.

Import semantics — the xlsx is authoritative for the visible table:
- Row present with a known hex_id  -> existing row; URL updated if edited.
- Row present with no hex_id       -> new row (source "Direct Input").
- Known hex_id absent from the file -> row marked deleted=1. The row stays
  in manifest.csv (hex_id reserved, cached data kept); it just no longer
  shows in the table.
Unknown hex_ids in the file are rejected rather than guessed at.
"""

from core.workfile.state.workfile_file import (
    MANIFEST_FIELDNAMES, new_manifest_row, renumber_chart_refs,
)
from core.acquisition.manifest_table.xlsx_writer import EXPORT_COLUMNS

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def read_manifest_xlsx(path) -> list[dict]:
    """
    Read the manifest .xlsx (path or file-like buffer) and return a list of
    {hex_id, url} dicts, one per non-empty data row. Only these two columns
    matter on the way back in; everything else is system-populated.
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required to read the manifest xlsx.")

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    hex_col = EXPORT_COLUMNS.index("hex_id")
    url_col = EXPORT_COLUMNS.index("url")

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(v is not None and str(v).strip() for v in row):
            continue  # skip empty rows
        hex_id = str(row[hex_col]).strip() if hex_col < len(row) and row[hex_col] is not None else ""
        url    = str(row[url_col]).strip() if url_col < len(row) and row[url_col] is not None else ""
        rows.append({"hex_id": hex_id, "url": url})
    return rows


def apply_manifest_import(imported: list[dict], *, workfile_state) -> dict:
    """
    Apply read_manifest_xlsx output to the manifest table per the import
    semantics above. Returns
    {"added": int, "updated": int, "deleted": int, "unknown_hex_ids": list}.
    """
    by_hex = {r["hex_id"]: r for r in workfile_state.manifest_rows if r.get("hex_id")}

    seen_hex_ids = set()
    added = updated = 0
    unknown = []

    for imp in imported:
        hex_id = imp["hex_id"]
        url = imp["url"]
        if hex_id:
            existing = by_hex.get(hex_id)
            if existing is None:
                unknown.append(hex_id)
                continue
            seen_hex_ids.add(hex_id)
            if url and url != existing.get("url", "").strip():
                existing["url"] = url
                updated += 1
            if str(existing.get("deleted", "0")) == "1":
                existing["deleted"] = "0"  # present in the file = wanted
                updated += 1
        elif url:
            row = new_manifest_row(url, "Direct Input", workfile_state.manifest_rows)
            workfile_state.manifest_rows.append(row)
            by_hex[row["hex_id"]] = row
            seen_hex_ids.add(row["hex_id"])
            added += 1

    # Known live rows missing from the file -> deleted
    deleted = 0
    for row in workfile_state.manifest_rows:
        if (row.get("hex_id") and row["hex_id"] not in seen_hex_ids
                and str(row.get("deleted", "0")) != "1"):
            row["deleted"] = "1"
            deleted += 1

    renumber_chart_refs(workfile_state.manifest_rows)
    workfile_state.dirty = True

    return {"added": added, "updated": updated, "deleted": deleted,
            "unknown_hex_ids": unknown}
