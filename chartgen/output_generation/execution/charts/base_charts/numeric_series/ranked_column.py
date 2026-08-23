"""Base Chart, NumericSeries. Ranked descending column chart with mean, median and quartile reference lines."""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker


BAR_BLUE     = "#7CB9E8"
MEAN_COL     = "#E87722"
MEDIAN_COL   = "#4CAF50"
QUARTILE_COL = "#888888"
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


def _resolve_unit_colours(units, population_layers):
    colours = [BAR_BLUE] * len(units)
    peer_colour_idx = 0
    for layer in population_layers:
        if layer.population_label == "All":
            continue
        colour = HIGHLIGHT if layer.population_label == "Selected" else PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
        if layer.population_label != "Selected":
            peer_colour_idx += 1
        ids = {u.unit_id for u in layer.units}
        for i, u in enumerate(units):
            if u.unit_id in ids:
                colours[i] = colour
    return colours


def _population_legend_handles(population_layers, data_label):
    handles = [mpatches.Patch(color=BAR_BLUE, label=data_label)]
    peer_colour_idx = 0
    for layer in population_layers:
        if layer.population_label == "All":
            continue
        if layer.population_label == "Selected":
            handles.append(mpatches.Patch(color=HIGHLIGHT, label="Selected"))
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            handles.append(mpatches.Patch(color=colour, label=layer.population_label))
            peer_colour_idx += 1
    return handles


def _find_selected_in_scope(units, population_layers):
    selected_layer = next((l for l in population_layers if l.population_label == "Selected"), None)
    if selected_layer is None or not selected_layer.units:
        return None, None, None
    sel_id = selected_layer.units[0].unit_id
    for i, u in enumerate(units):
        if u.unit_id == sel_id:
            return i, u.values[0], u.unit_code
    return None, None, None


def ranked_column(population_layers: list, width_emu=5486400, height_emu=3429000, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    ms = base.metric_stats[0]
    units = sorted(base.units, key=lambda u: (u.values[0] is None, -(u.values[0] or 0)))
    codes  = [u.unit_code for u in units]
    values = [u.values[0] if u.values[0] is not None else 0 for u in units]
    x = np.arange(len(codes))

    colours = _resolve_unit_colours(units, population_layers)
    ax.bar(x, values, color=colours, width=0.8, zorder=2)

    sel_idx, sel_val, sel_code = _find_selected_in_scope(units, population_layers)
    if sel_idx is not None and sel_val is not None:
        ax.annotate(sel_code,
                    xy=(sel_idx, sel_val), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=7 * TEXT_SCALE, color=HIGHLIGHT, fontweight="bold")

    if ms.mean   is not None: ax.axhline(ms.mean,   color=MEAN_COL,    linewidth=1.5 * TEXT_SCALE, zorder=3)
    if ms.median is not None: ax.axhline(ms.median, color=MEDIAN_COL,  linewidth=1.5 * TEXT_SCALE, zorder=3)
    if ms.q1     is not None: ax.axhline(ms.q1,     color=QUARTILE_COL, linewidth=1 * TEXT_SCALE, linestyle="--", zorder=3)
    if ms.q3     is not None: ax.axhline(ms.q3,     color=QUARTILE_COL, linewidth=1 * TEXT_SCALE, linestyle="--", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(codes, rotation=90, fontsize=7 * TEXT_SCALE)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=8 * TEXT_SCALE)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)

    label = base.metric_names[0] if base.metric_names else "Value"
    handles = _population_legend_handles(population_layers, label)
    handles += [
        plt.Line2D([0],[0], color=MEAN_COL,     linewidth=1.5 * TEXT_SCALE, label="Mean"),
        plt.Line2D([0],[0], color=MEDIAN_COL,   linewidth=1.5 * TEXT_SCALE, label="Median"),
        plt.Line2D([0],[0], color=QUARTILE_COL, linewidth=1 * TEXT_SCALE, linestyle="--", label="Lower/Upper Quartiles"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.28),
              ncol=4, fontsize=7 * TEXT_SCALE, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig)
