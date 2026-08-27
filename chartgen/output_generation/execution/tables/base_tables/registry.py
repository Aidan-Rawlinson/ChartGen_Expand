"""
registry.py
Maps table_type_ref to its Base Table function.

Five built-ins: plain_grid, table_cardtile, and their two-row-header
CI-report variants ci_grid, ci_cardtile and ci_cardtile2. One standalone
file each.
Adding a rendering style is a registry entry, not a change to insert_table
or the Output Tables tab.
"""

from chartgen.output_generation.execution.tables.base_tables.plain_grid import plain_grid
from chartgen.output_generation.execution.tables.base_tables.table_cardtile import table_cardtile
from chartgen.output_generation.execution.tables.base_tables.ci_grid import ci_grid
from chartgen.output_generation.execution.tables.base_tables.ci_cardtile import ci_cardtile
from chartgen.output_generation.execution.tables.base_tables.ci_cardtile2 import ci_cardtile2

TABLE_REGISTRY = {
    "plain_grid": plain_grid,
    "table_cardtile": table_cardtile,
    "ci_grid": ci_grid,
    "ci_cardtile": ci_cardtile,
    "ci_cardtile2": ci_cardtile2,
}
