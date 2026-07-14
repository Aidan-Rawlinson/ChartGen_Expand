"""
base_charts/
Base Chart functions — one per chart type reference, split by canonical data
shape (numeric_series, numeric_compositional, categorical_compositional),
with shared palette/rendering helpers in shared.py and the dispatch table in
registry.py. This __init__ re-exports CHART_REGISTRY and render_chart so
external call sites are unaffected by the split.
"""

from core.output_generation.execution.charts.base_charts.registry import (
    CHART_REGISTRY,
    render_chart,
)

__all__ = ["CHART_REGISTRY", "render_chart"]
