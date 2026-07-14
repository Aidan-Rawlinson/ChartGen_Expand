"""
running_order/
Manages the Running Order — the row-based instruction list that drives report
assembly — as a list of row dicts, with .xlsx export/import for human editing.

Split into: schema (columns, function/scope constants), dialog_support
(row-edit dialog's chart-type filtering and populations-string logic),
generation (building rows from a template read result), xlsx_writer, and
xlsx_reader. This __init__ re-exports the full public API so external call
sites are unaffected by the split.
"""

from core.output_generation.definition.running_order.schema import (
    COLUMNS,
    ALL_FUNCTIONS,
    SCOPE_VALUES,
    STRUCTURAL_FUNCTIONS,
    CONTENT_FUNCTIONS,
    BATCH_FUNCTIONS,
)
from core.output_generation.definition.running_order.dialog_support import (
    get_valid_chart_refs_for_cache_file,
    build_populations_options,
    parse_populations_string,
    build_populations_string,
)
from core.output_generation.definition.running_order.generation import (
    generate_from_template,
)
from core.output_generation.definition.running_order.xlsx_writer import write_xlsx
from core.output_generation.definition.running_order.xlsx_reader import read_xlsx

__all__ = [
    "COLUMNS",
    "ALL_FUNCTIONS",
    "SCOPE_VALUES",
    "STRUCTURAL_FUNCTIONS",
    "CONTENT_FUNCTIONS",
    "BATCH_FUNCTIONS",
    "get_valid_chart_refs_for_cache_file",
    "build_populations_options",
    "parse_populations_string",
    "build_populations_string",
    "generate_from_template",
    "write_xlsx",
    "read_xlsx",
]
