"""
constants.py
Generic record-shape constants and CSV/WorkfileState field-type coercion.
Renamed from constants_temp.py — the "temp" marker no longer applies now
this restructure has landed.

Audited against Restructure_Plan.md Open Item 2: only coerce_row/FIELD_TYPES
are genuinely generic (used by api_client, running_order, and workfile_file,
with no domain knowledge of any one of them).
"""

FIELD_TYPES = {
    "submission_id":   str,
    "unit_id":         str,
    "organisation_id": str,
    "enabled":         "bool_int",
}

# Population-table shared spine, display/authoring order. Any column not in
# this list (Name() peer-group columns) follows after, in the order it
# appears on the row. Used by the UI (column display order) and the Excel
# round-trip (export/import column order) — one definition, not two.
SPINE_COLUMN_ORDER = ["unit_id", "unit_code", "unit_name", "soft_parents"]


def coerce_row(row: dict, field_types: dict = FIELD_TYPES) -> dict:
    """Coerce known fields in a dict to their canonical type in place; fields not present are left untouched."""
    for field, target in field_types.items():
        if field not in row:
            continue
        value = row[field]
        if target is str:
            row[field] = "" if value is None else str(value)
        elif target == "bool_int":
            row[field] = 1 if str(value).strip() in ("1", "True", "true", "yes") else 0
    return row
