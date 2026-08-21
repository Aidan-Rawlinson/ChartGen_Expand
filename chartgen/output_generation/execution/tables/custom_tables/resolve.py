"""
resolve.py
Resolves a table_type_ref to a callable (built-in first, custom second),
and lists a workfile's saved custom tables wherever table types are shown
to the user -- currently just the Output Tables tab's own Visualisation
picker.

Unlike the chart equivalent, there is no shape_type dimension to filter
by -- every Base Table takes the same table_inputs (an already-resolved
grid), so every custom table is a valid option everywhere, always.
"""

from chartgen.output_generation.execution.tables.base_tables import TABLE_REGISTRY
from chartgen.output_generation.execution.tables.custom_tables.gate import (
    compile_custom_table, CustomTableError,
)


def get_table_callable(table_type_ref: str, custom_table_code: dict):
    """
    Resolve a table_type_ref to a callable -- built-in registry first, then
    the workfile's own saved custom tables. Raises ValueError if neither
    has it. Raises CustomTableError if a custom table's stored source no
    longer compiles (should not happen for anything that passed the gate
    at save time, but a workfile can be hand-edited outside the app).
    """
    if table_type_ref in TABLE_REGISTRY:
        return TABLE_REGISTRY[table_type_ref]
    if custom_table_code and table_type_ref in custom_table_code:
        return compile_custom_table(custom_table_code[table_type_ref])
    raise ValueError(f"Unknown table_type_ref: {table_type_ref}")


def custom_table_descriptions(custom_table_rows: list) -> list:
    """
    Return (table_type_ref, description) pairs for this workfile's saved
    custom tables, in the same shape a dropdown's description map expects.
    """
    if not custom_table_rows:
        return []
    pairs = []
    for r in custom_table_rows:
        notes = str(r.get("notes", "") or "").strip()
        desc = f"Custom: {r['table_type_ref']} — {notes}" if notes else f"Custom: {r['table_type_ref']}"
        pairs.append((r["table_type_ref"], desc))
    return pairs


def all_table_type_refs(custom_table_rows: list) -> list:
    """Built-in refs followed by this workfile's saved custom refs, in that order."""
    built_in = list(TABLE_REGISTRY.keys())
    custom = [r["table_type_ref"] for r in (custom_table_rows or [])]
    return built_in + custom
