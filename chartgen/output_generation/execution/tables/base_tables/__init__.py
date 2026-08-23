"""Base Tables, the table equivalent of base_charts/. Dispatch in registry.py."""

from chartgen.output_generation.execution.tables.base_tables.registry import (
    TABLE_REGISTRY,
    render_table,
)

__all__ = ["TABLE_REGISTRY", "render_table"]
