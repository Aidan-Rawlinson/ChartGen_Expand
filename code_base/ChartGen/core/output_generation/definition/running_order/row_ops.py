"""
row_ops.py
Generic Running Order row operations used by the Charts sheet's save-back
control (Overwrite / Insert above / Insert below). Deliberately separate
from generation.py (builds rows from a template read result) and
dialog_support.py (row-edit dialog validity rules) — this module only
moves rows around a list and renumbers row_id, with no knowledge of charts,
shapes, or the Charts sheet itself.
"""

from core.output_generation.definition.running_order.schema import COLUMNS


def renumber_row_ids(rows: list[dict]):
    """Reassign row_id sequentially (1-based) in list order, in place."""
    for i, row in enumerate(rows, start=1):
        row["row_id"] = i


def overwrite_row_fields(rows: list[dict], target_index: int, field_values: dict):
    """
    Overwrite the given fields on rows[target_index] in place. Every other
    column on that row (position, scope, notes, etc.) is left untouched.
    """
    rows[target_index].update(field_values)


def insert_new_row(rows: list[dict], target_index: int, field_values: dict,
                    position: str) -> int:
    """
    Insert a new Running Order row copied from rows[target_index] for every
    column not in field_values, with field_values applied on top, placed
    immediately above or below the target row. row_id is renumbered for the
    whole list afterwards.

    position: "above" or "below".
    Returns the new row's index in the (now renumbered) list.
    """
    template_row = rows[target_index]
    new_row = {col: template_row.get(col, "") for col in COLUMNS}
    new_row.update(field_values)

    insert_at = target_index if position == "above" else target_index + 1
    rows.insert(insert_at, new_row)
    renumber_row_ids(rows)
    return insert_at
