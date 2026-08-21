"""
base_charts/
Base Chart functions — one module per chart type reference, grouped into a
folder per canonical data shape (numeric_series/, numeric_compositional/,
categorical_compositional/, timeseries/), with dispatch in registry.py.

Each Base Chart function is a standalone artefact: no imports from
ChartGen's own code, only third-party libraries (matplotlib, numpy). It
receives chart_inputs only — population_layers, width_emu, height_emu, tweaks —
and returns image_bytes only. There is no shared internal helpers module;
each function carries its own copy of whatever palette/formatting/sizing
logic it needs. This is deliberate, not an oversight: a Base Chart is
treated the same way an Excel .crtx chart-type template is treated — a
rendering artefact, not application logic — and a future custom chart
(user- or AI-authored, stored in the .cgw) must be reviewable and editable
in exactly the same way as any of these, with no hidden dependency on code
it can't see.

This __init__ re-exports CHART_REGISTRY and render_chart so external call
sites are unaffected by the module layout.
"""

from chartgen.output_generation.execution.charts.base_charts.registry import (
    CHART_REGISTRY,
    render_chart,
)

__all__ = ["CHART_REGISTRY", "render_chart"]
