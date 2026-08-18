"""
registry.py
Chart registry and dispatch — maps base_chart_name to its Base Chart function
across all four data shapes.

Each Base Chart function is a standalone artefact (its own module, no
imports from ChartGen's own code) — this is the one place in the codebase
that treats them as a set. render_chart's signature is the chart_inputs
contract every Base Chart, built-in or custom, must accept:
population_layers, width_emu, height_emu, tweaks. No report_context or any other
runtime object is passed through.

Before adding a new Base Chart: check the proposed registry key, file
name, and function name against CHART_REGISTRY and the base_charts
folder. Base Chart files arrive externally-authored (download/AI-edit/
paste-back), so a file's own internal module docstring or function name
may be stale or coincidentally match an existing entry — a name match is
not evidence the file is meant to replace that entry. Flag any collision
and confirm with the user before overwriting or reusing an existing
key/file/function name; do not assume replacement was intended.
"""

from core.output_generation.execution.charts.base_charts.numeric_series.ranked_column import ranked_column
from core.output_generation.execution.charts.base_charts.numeric_series.dot_strip import dot_strip
from core.output_generation.execution.charts.base_charts.numeric_series.box_whisker import box_whisker
from core.output_generation.execution.charts.base_charts.numeric_series.frequency_histogram import frequency_histogram
from core.output_generation.execution.charts.base_charts.numeric_series.violin_plot import violin_plot
from core.output_generation.execution.charts.base_charts.numeric_series.bead_string_dot_plot import bead_string_dot_plot
from core.output_generation.execution.charts.base_charts.numeric_series.column_ci_full import column_ci_full

from core.output_generation.execution.charts.base_charts.numeric_compositional.ugly_bar import ugly_bar
from core.output_generation.execution.charts.base_charts.numeric_compositional.radar_chart import radar_chart
from core.output_generation.execution.charts.base_charts.numeric_compositional.donut_component import donut_component
from core.output_generation.execution.charts.base_charts.numeric_compositional.lollipop_chart import lollipop_chart
from core.output_generation.execution.charts.base_charts.numeric_compositional.waffle_chart import waffle_chart

from core.output_generation.execution.charts.base_charts.categorical_compositional.yn_bar import yn_bar
from core.output_generation.execution.charts.base_charts.categorical_compositional.list_pie import list_pie
from core.output_generation.execution.charts.base_charts.categorical_compositional.diverging_bar import diverging_bar
from core.output_generation.execution.charts.base_charts.categorical_compositional.dot_matrix import dot_matrix
from core.output_generation.execution.charts.base_charts.categorical_compositional.donut_pie import donut_pie
from core.output_generation.execution.charts.base_charts.categorical_compositional.treemap import treemap

from core.output_generation.execution.charts.base_charts.timeseries.period_line_chart import period_line_chart
from core.output_generation.execution.charts.base_charts.timeseries.median_comparison_linechart import median_comparison_linechart
from core.output_generation.execution.charts.base_charts.timeseries.full_lines_linechart import full_lines_linechart
from core.output_generation.execution.charts.base_charts.timeseries.sparkline1 import sparkline1
from core.output_generation.execution.charts.base_charts.timeseries.celltest import celltest
from core.output_generation.execution.charts.base_charts.timeseries.line_has_data import line_has_data
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_at_least_median import line_ci_at_least_median
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_at_most_median import line_ci_at_most_median
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_at_most_2 import line_ci_at_most_2
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_at_most_5pct import line_ci_at_most_5pct
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_0 import line_ci_0
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_at_least_90pct import line_ci_at_least_90pct
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_100pct import line_ci_100pct
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_full import line_ci_full
from core.output_generation.execution.charts.base_charts.timeseries.line_ci_na import line_ci_na

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
    "column_ci_full":       column_ci_full,
    "period_line_chart":    period_line_chart,
    "median_comparison_linechart": median_comparison_linechart,
    "full_lines_linechart": full_lines_linechart,
    "sparkline1":           sparkline1,
    "celltest":             celltest,
    "line_has_data":        line_has_data,
    "line_ci_at_least_median": line_ci_at_least_median,
    "line_ci_at_most_median":  line_ci_at_most_median,
    "line_ci_at_most_2":       line_ci_at_most_2,
    "line_ci_at_most_5pct":    line_ci_at_most_5pct,
    "line_ci_0":               line_ci_0,
    "line_ci_at_least_90pct":  line_ci_at_least_90pct,
    "line_ci_100pct":          line_ci_100pct,
    "line_ci_full":         line_ci_full,
    "line_ci_na":           line_ci_na,
}


def render_chart(base_chart_name: str, population_layers: list,
                 width_emu: int, height_emu: int, tweaks=""):
    """
    Returns image_bytes only — a Base Chart function's sole job is
    producing the visual. Statistics and unit lists are a property of the
    data shape (core.shared.normalisation_containers.shapes), not something
    the charting layer computes or relays: a caller that needs them already
    has population_layers in scope and calls summary_stats_by_layer /
    units_by_layer directly, rather than routing through here.

    chart_inputs contract: population_layers, width_emu, height_emu, tweaks. No
    report_context or any other ChartGen runtime object is passed to a
    Base Chart function — Selected-unit identity is read from the
    "Selected"-labelled entry in population_layers by whichever chart
    needs it.
    """
    if base_chart_name not in CHART_REGISTRY:
        raise ValueError(f"Unknown base_chart_name: {base_chart_name}")
    return CHART_REGISTRY[base_chart_name](
        population_layers, width_emu=width_emu, height_emu=height_emu, tweaks=tweaks,
    )
