"""
median_comparison_linechart.py
Base Chart — TimeSeries. Median per population layer across every period;
Selected charts the actual unit value(s) instead of a median, since a
median of one unit's own value(s) isn't a meaningful statistic in the way
it is for a wider population.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) — no report_context or any other runtime object. The
Selected unit's label comes from its own unit_code in the
"Selected"-labelled population layer.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font, baked into the SVG
# vector output as real glyph outlines (svg.fonttype default "path").
# See Architecture, SVG rendering methodology.
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

NAVY         = "#1F4E79"
HIGHLIGHT    = "#C12958"
PEER_COLOURS = ["#2E9E75", "#7030A0", "#E87722", "#2E86AB"]

EMU_PER_INCH = 914400


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _apply_spine_style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


def _format_number(value, format_modifier):
    if value is None:
        return ""
    if format_modifier == "P":
        return f"{value:,.0f}%"
    if format_modifier == "C":
        return f"£{value:,.0f}"
    return f"{value:,.0f}"


def _axis_formatter(format_modifier):
    return mticker.FuncFormatter(lambda v, _: _format_number(v, format_modifier))


def median_comparison_linechart(population_layers: list, width_emu=5486400, height_emu=3086100, tweaks=""):
    """Line chart of one Metric-Series across every period — median line per population layer, except 'Selected', which charts the actual unit value(s) instead of a median."""
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig)

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig)

    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    x = np.arange(len(base.periods))
    labels = [p.period_label for p in base.periods]

    peer_colour_idx = 0

    for i, layer in enumerate(population_layers):
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue

        if layer.population_label == "Selected":
            for unit in layer_metric.units:
                ax.plot(x, unit.values, color=HIGHLIGHT, linewidth=2, marker="o",
                        markersize=4, zorder=4)
            if layer_metric.units:
                ax.plot([], [], color=HIGHLIGHT, linewidth=2, marker="o", markersize=4,
                        label=layer_metric.units[0].unit_code)
        elif i == 0:
            medians = [ps.median for ps in layer_metric.period_stats]
            ax.plot(x, medians, color=NAVY, linewidth=2, zorder=2,
                    label=f"{layer.population_label} median")
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            medians = [ps.median for ps in layer_metric.period_stats]
            ax.plot(x, medians, color=colour, linewidth=1.5, linestyle="--", zorder=3,
                    label=f"{layer.population_label} median")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()

    return _fig_to_bytes(fig)
