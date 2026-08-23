"""Base Charts, grouped into a folder per canonical data shape. Dispatch in registry.py."""

from chartgen.output_generation.execution.charts.base_charts.registry import (
    CHART_REGISTRY,
    render_chart,
)

__all__ = ["CHART_REGISTRY", "render_chart"]
