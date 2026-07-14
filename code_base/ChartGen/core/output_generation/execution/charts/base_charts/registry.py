"""
registry.py
Chart registry and dispatch — maps chart_type_ref to its Base Chart function
across all three data shapes.
"""

from core.output_generation.execution.charts.base_charts.numeric_series import (
    ranked_column, dot_strip, box_whisker, frequency_histogram, violin_plot,
    bead_string_dot_plot,
)
from core.output_generation.execution.charts.base_charts.numeric_compositional import (
    ugly_bar, radar_chart, donut_component, lollipop_chart, waffle_chart,
)
from core.output_generation.execution.charts.base_charts.categorical_compositional import (
    yn_bar, list_pie, diverging_bar, dot_matrix, donut_pie, treemap,
)

CHART_REGISTRY = {
    "ranked_column":        ranked_column,
    "dot_strip":            dot_strip,
    "box_whisker":          box_whisker,
    "frequency_histogram":  frequency_histogram,
    "violin_plot":          violin_plot,
    "ugly_bar":             ugly_bar,
    "radar_chart":          radar_chart,
    "donut_component":      donut_component,
    "lollipop_chart":       lollipop_chart,
    "waffle_chart":         waffle_chart,
    "yn_bar":               yn_bar,
    "list_pie":             list_pie,
    "diverging_bar":        diverging_bar,
    "dot_matrix":           dot_matrix,
    "donut_pie":            donut_pie,
    "treemap":              treemap,
    "bead_string_dot_plot": bead_string_dot_plot,
}


def render_chart(chart_type_ref: str, population_layers: list,
                 width: int, height: int, tweaks=[], report_context=None):
    if chart_type_ref not in CHART_REGISTRY:
        raise ValueError(f"Unknown chart_type_ref: {chart_type_ref}")
    return CHART_REGISTRY[chart_type_ref](
        population_layers, width=width, height=height,
        tweaks=tweaks, report_context=report_context,
    )
