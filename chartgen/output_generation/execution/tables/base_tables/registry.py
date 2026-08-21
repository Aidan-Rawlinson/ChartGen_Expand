"""
registry.py
Table registry and dispatch -- maps table_type_ref to its Base Table
function. The base_tables equivalent of
chartgen.output_generation.execution.charts.base_charts.registry.

Four built-in table_type_refs -- plain_grid (the minimal first pass),
table_cardtile, and their two-row-header CI-report variants ci_grid and
ci_cardtile -- each its own standalone file, one table_type_ref per
file, exactly as the built-in Base Charts are laid out. Extending this to
further rendering styles is a registry entry, not a change to insert_table
or the Output Tables tab.

Trimmed back from ten styles to plain_grid/table_cardtile (Decisions.md) --
chart-component cells (Decision 28) surfaced a harder problem several of
the removed styles hadn't solved yet: each Base Table function is its own
standalone artefact responsible for reporting back where it actually
draws a cell, and a style with deliberately-overflowing decoration
(a bleeding tab, a bleeding badge, drop shadows) needs to account for that
in its own reported rectangle, not simply drop bbox_inches="tight" the
way plain_grid could. table_cardtile is being kept specifically to work
through that harder case, rather than repeating the fix nine more times
speculatively. ci_grid/ci_cardtile were added afterward, once that harder
case was worked through, as CI-report-specific two-row-header variants.
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
    Returns image_bytes only. table_inputs contract: content (already-
    resolved grid), column_widths, row_heights, width_emu, height_emu, tweaks -- no
    other ChartGen runtime object is passed to a Base Table function.
    """
    if table_type_ref not in TABLE_REGISTRY:
        raise ValueError(f"Unknown table_type_ref: {table_type_ref}")
    return TABLE_REGISTRY[table_type_ref](
        content, column_widths, row_heights, width_emu=width_emu, height_emu=height_emu, tweaks=tweaks,
    )
