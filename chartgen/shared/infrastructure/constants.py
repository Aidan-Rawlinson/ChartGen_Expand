"""
constants.py
Generic record-shape constants and CSV/WorkfileState field-type coercion.
Used by api_client, running_order and workfile_file alike, with no domain
knowledge of any of them.
"""

FIELD_TYPES = {
    "submission_id":   str,
    "unit_id":         str,
    "organisation_id": str,
    "enabled":         "bool_int",
}

# Population-table shared spine, in display/authoring order. Any column not
# listed here (Name() peer-group columns) follows after, in the order it
# appears on the row. Read by both the UI's column display order and the
# Excel round-trip's export/import order.
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
