"""
base_tables/
Base Table functions -- the table equivalent of
core/output_generation/execution/charts/base_charts/. Each is a standalone
artefact -- no imports from ChartGen's own code, only third-party
libraries (matplotlib) -- taking table_inputs only (content, column_widths,
row_heights, width, height, tweaks) and returning image_bytes only.
Dispatch is in registry.py.

Only one table_type_ref exists so far (plain_grid) -- a deliberately
minimal first pass (Decisions.md). A Base Table is treated exactly the way
a Base Chart is: a rendering artefact, not application logic, reviewable
and editable in full, which is what makes Custom Tables
(execution/tables/custom_tables/) possible on the same terms as Custom
Charts.

This __init__ re-exports TABLE_REGISTRY and render_table so external call
sites are unaffected by the module layout.
"""

from core.output_generation.execution.tables.base_tables.registry import (
    TABLE_REGISTRY,
    render_table,
)

__all__ = ["TABLE_REGISTRY", "render_table"]
