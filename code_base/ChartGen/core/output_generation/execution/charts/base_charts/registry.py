"""
registry.py
Chart registry and dispatch — maps chart_type_ref to its Base Chart function
across all four data shapes.
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
from core.output_generation.execution.charts.base_charts.timeseries import (
    period_line_chart, median_comparison_linechart, full_lines_linechart,
)
from core.shared.normalisation_containers.shapes import summary_stats_by_layer, units_by_layer

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
    "period_line_chart":    period_line_chart,
    "median_comparison_linechart": median_comparison_linechart,
    "full_lines_linechart": full_lines_linechart,
}


def render_chart(chart_type_ref: str, population_layers: list,
                 width: int, height: int, tweaks=[], report_context=None):
    """
    Returns (image_bytes, base_summary_stats, layer_summary_stats, layer_units).

    base_summary_stats is unchanged from before — the scope layer's own
    stats plus the selected-unit bolt-on fields, as each Base Chart function
    already builds it.

    layer_summary_stats and layer_units are the correction: every population
    layer passed in gets its own stats and its own unit list read
    (population_label -> that layer's own existing data), not just the
    scope layer. Computed here, once, regardless of chart type, rather than
    inside each of the 20 Base Chart functions.
    """
    if chart_type_ref not in CHART_REGISTRY:
        raise ValueError(f"Unknown chart_type_ref: {chart_type_ref}")
    image_bytes, base_summary_stats = CHART_REGISTRY[chart_type_ref](
        population_layers, width=width, height=height,
        tweaks=tweaks, report_context=report_context,
    )
    layer_summary_stats = summary_stats_by_layer(population_layers)
    layer_units = units_by_layer(population_layers)
    return image_bytes, base_summary_stats, layer_summary_stats, layer_units
