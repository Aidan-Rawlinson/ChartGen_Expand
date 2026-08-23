"""
registry.py
Maps table_type_ref to its Base Table function.

Four built-ins: plain_grid, table_cardtile, and their two-row-header
CI-report variants ci_grid and ci_cardtile. One standalone file each.
Adding a rendering style is a registry entry, not a change to insert_table
or the Output Tables tab.
"""

from chartgen.output_generation.execution.tables.base_tables.plain_grid import plain_grid
from chartgen.output_generation.execution.tables.base_tables.table_cardtile import table_cardtile
from chartgen.output_generation.execution.tables.base_tables.ci_grid import ci_grid
from chartgen.output_generation.execution.tables.base_tables.ci_cardtile import ci_cardtile

TABLE_REGISTRY = {
    "plain_grid": plain_grid,
    "table_cardtile": table_cardtile,
    "ci_grid": ci_grid,
    "ci_cardtile": ci_cardtile,
}


def render_table(table_type_ref: str, content: list, column_widths: list,
                 row_heights: list, width_emu: int, height_emu: int, tweaks=""):
    """
    UNUSED. insert_table.py calls the registered function directly.

    table_inputs contract: content (already-resolved grid), column_widths,
    row_heights, width_emu, height_emu, tweaks. Returns
    (image_bytes, chart_cells). No other ChartGen runtime object is passed
    to a Base Table function.
    """
    if table_type_ref not in TABLE_REGISTRY:
        raise ValueError(f"Unknown table_type_ref: {table_type_ref}")
    return TABLE_REGISTRY[table_type_ref](
        content, column_widths, row_heights, width_emu=width_emu, height_emu=height_emu, tweaks=tweaks,
    )
