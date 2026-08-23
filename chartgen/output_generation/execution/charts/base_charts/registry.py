"""
registry.py
Maps base_chart_name to its Base Chart function. The one place in the
codebase that treats Base Charts as a set; each is otherwise a standalone
artefact importing nothing from ChartGen.

render_chart's signature is the chart_inputs contract every Base Chart,
built-in or custom, must accept: population_layers, width_emu, height_emu,
tweaks.

Before adding one, check the proposed registry key, file name and function
name against CHART_REGISTRY and the base_charts folder. These files arrive
externally authored, so a file's own docstring or function name may be stale
or may coincidentally match an existing entry. A name match is not evidence
that replacement was intended: flag any collision and confirm before
overwriting.
"""

from chartgen.output_generation.execution.charts.base_charts.numeric_series.ranked_column import ranked_column
from chartgen.output_generation.execution.charts.base_charts.numeric_series.dot_strip import dot_strip
from chartgen.output_generation.execution.charts.base_charts.numeric_series.box_whisker import box_whisker
from chartgen.output_generation.execution.charts.base_charts.numeric_series.frequency_histogram import frequency_histogram
from chartgen.output_generation.execution.charts.base_charts.numeric_series.violin_plot import violin_plot
from chartgen.output_generation.execution.charts.base_charts.numeric_series.bead_string_dot_plot import bead_string_dot_plot
from chartgen.output_generation.execution.charts.base_charts.numeric_series.column_ci_full import column_ci_full

from chartgen.output_generation.execution.charts.base_charts.numeric_compositional.ugly_bar import ugly_bar
from chartgen.output_generation.execution.charts.base_charts.numeric_compositional.radar_chart import radar_chart
from chartgen.output_generation.execution.charts.base_charts.numeric_compositional.donut_component import donut_component
from chartgen.output_generation.execution.charts.base_charts.numeric_compositional.lollipop_chart import lollipop_chart
from chartgen.output_generation.execution.charts.base_charts.numeric_compositional.waffle_chart import waffle_chart

from chartgen.output_generation.execution.charts.base_charts.categorical_compositional.yn_bar import yn_bar
from chartgen.output_generation.execution.charts.base_charts.categorical_compositional.list_pie import list_pie
from chartgen.output_generation.execution.charts.base_charts.categorical_compositional.diverging_bar import diverging_bar
from chartgen.output_generation.execution.charts.base_charts.categorical_compositional.dot_matrix import dot_matrix
from chartgen.output_generation.execution.charts.base_charts.categorical_compositional.donut_pie import donut_pie
from chartgen.output_generation.execution.charts.base_charts.categorical_compositional.treemap import treemap

from chartgen.output_generation.execution.charts.base_charts.timeseries.period_line_chart import period_line_chart
from chartgen.output_generation.execution.charts.base_charts.timeseries.median_comparison_linechart import median_comparison_linechart
from chartgen.output_generation.execution.charts.base_charts.timeseries.full_lines_linechart import full_lines_linechart
from chartgen.output_generation.execution.charts.base_charts.timeseries.sparkline1 import sparkline1
from chartgen.output_generation.execution.charts.base_charts.timeseries.celltest import celltest
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_has_data import line_has_data
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_at_least_median import line_ci_at_least_median
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_at_most_median import line_ci_at_most_median
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_at_most_2 import line_ci_at_most_2
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_at_most_5pct import line_ci_at_most_5pct
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_0 import line_ci_0
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_at_least_90pct import line_ci_at_least_90pct
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_100pct import line_ci_100pct
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_full import line_ci_full
from chartgen.output_generation.execution.charts.base_charts.timeseries.line_ci_na import line_ci_na

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
    Returns image_bytes only. Statistics and unit lists are a property of the
    data shape, not something the charting layer computes or relays: a caller
    that needs them already holds population_layers and calls
    summary_stats_by_layer or units_by_layer directly.

    chart_inputs contract: population_layers, width_emu, height_emu, tweaks.
    No report_context or other runtime object is passed. Selected-unit
    identity is read from the "Selected"-labelled population_layers entry.
    """
    if base_chart_name not in CHART_REGISTRY:
        raise ValueError(f"Unknown base_chart_name: {base_chart_name}")
    return CHART_REGISTRY[base_chart_name](
        population_layers, width_emu=width_emu, height_emu=height_emu, tweaks=tweaks,
    )
