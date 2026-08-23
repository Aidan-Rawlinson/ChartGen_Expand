"""Base Chart, TimeSeries. Median per population layer across every period, except Selected, which charts the actual unit values."""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

NAVY         = "#1F4E79"
HIGHLIGHT    = "#C12958"
PEER_COLOURS = ["#2E9E75", "#7030A0", "#E87722", "#2E86AB"]

EMU_PER_INCH = 914400

TEXT_SCALE = 5


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
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=10 * TEXT_SCALE)
        return _fig_to_bytes(fig)

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=10 * TEXT_SCALE)
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
                ax.plot(x, unit.values, color=HIGHLIGHT, linewidth=2 * TEXT_SCALE, marker="o",
                        markersize=4 * TEXT_SCALE, zorder=4)
            if layer_metric.units:
                ax.plot([], [], color=HIGHLIGHT, linewidth=2 * TEXT_SCALE, marker="o", markersize=4 * TEXT_SCALE,
                        label=layer_metric.units[0].unit_code)
        elif i == 0:
            medians = [ps.median for ps in layer_metric.period_stats]
            ax.plot(x, medians, color=NAVY, linewidth=2 * TEXT_SCALE, zorder=2,
                    label=f"{layer.population_label} median")
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            medians = [ps.median for ps in layer_metric.period_stats]
            ax.plot(x, medians, color=colour, linewidth=1.5 * TEXT_SCALE, linestyle="--", zorder=3,
                    label=f"{layer.population_label} median")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7 * TEXT_SCALE)
    ax.tick_params(axis="y", labelsize=8 * TEXT_SCALE)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7 * TEXT_SCALE, frameon=False)
    fig.tight_layout()

    return _fig_to_bytes(fig)
