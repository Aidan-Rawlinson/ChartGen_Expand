"""
custom_charts/
Custom Charts — user- or AI-authored Base Chart functions, stored in the
.cgw alongside the built-ins, treated identically once saved.

  - contract.py  — single source of truth: allowed imports, banned names,
                   and the shared explanatory text used by both the gate
                   and the download bundle.
  - gate.py      — static validation (the "AST gate") and compilation of
                   custom chart source text into a callable.
  - resolve.py   — built-in-then-custom base_chart_name resolution, and the
                   dropdown-merge helpers used by the Charts sheet and
                   Running Order.
  - bundle.py    — builds the single-document download bundle handed to an
                   external AI session for editing a chart.
"""

from chartgen.output_generation.execution.charts.custom_charts.gate import (
    validate_custom_chart_code, compile_custom_chart, CustomChartError,
)
from chartgen.output_generation.execution.charts.custom_charts.resolve import (
    get_chart_callable, merge_custom_refs_for_shape, custom_chart_descriptions,
)
from chartgen.output_generation.execution.charts.custom_charts.bundle import build_bundle

__all__ = [
    "validate_custom_chart_code", "compile_custom_chart", "CustomChartError",
    "get_chart_callable", "merge_custom_refs_for_shape", "custom_chart_descriptions",
    "build_bundle",
]
