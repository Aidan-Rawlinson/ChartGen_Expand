"""
registry.py
Table registry and dispatch -- maps table_type_ref to its Base Table
function. The base_tables equivalent of
core.output_generation.execution.charts.base_charts.registry.

Ten built-in table_type_refs -- plain_grid (the minimal first pass) plus
nine styled alternatives (Decisions.md), each its own standalone file, one
table_type_ref per file, exactly as the built-in Base Charts are laid out.
Extending this to further rendering styles is a registry entry, not a
change to insert_table or the Output Tables tab.
"""

from core.output_generation.execution.tables.base_tables.plain_grid import plain_grid
from core.output_generation.execution.tables.base_tables.table_ledger import table_ledger
from core.output_generation.execution.tables.base_tables.table_zebra import table_zebra
from core.output_generation.execution.tables.base_tables.table_editorial import table_editorial
from core.output_generation.execution.tables.base_tables.table_terminal import table_terminal
from core.output_generation.execution.tables.base_tables.table_cardtile import table_cardtile
from core.output_generation.execution.tables.base_tables.table_pill import table_pill
from core.output_generation.execution.tables.base_tables.table_freeform import table_freeform
from core.output_generation.execution.tables.base_tables.table_brutalist import table_brutalist
from core.output_generation.execution.tables.base_tables.table_softui import table_softui

TABLE_REGISTRY = {
    "plain_grid": plain_grid,
    "table_ledger": table_ledger,
    "table_zebra": table_zebra,
    "table_editorial": table_editorial,
    "table_terminal": table_terminal,
    "table_cardtile": table_cardtile,
    "table_pill": table_pill,
    "table_freeform": table_freeform,
    "table_brutalist": table_brutalist,
    "table_softui": table_softui,
}


def render_table(table_type_ref: str, content: list, column_widths: list,
                 row_heights: list, width: int, height: int, tweaks=""):
    """
    Returns image_bytes only. table_inputs contract: content (already-
    resolved grid), column_widths, row_heights, width, height, tweaks -- no
    other ChartGen runtime object is passed to a Base Table function.
    """
    if table_type_ref not in TABLE_REGISTRY:
        raise ValueError(f"Unknown table_type_ref: {table_type_ref}")
    return TABLE_REGISTRY[table_type_ref](
        content, column_widths, row_heights, width=width, height=height, tweaks=tweaks,
    )
