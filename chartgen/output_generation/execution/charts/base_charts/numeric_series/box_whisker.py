"""Base Chart, NumericSeries. Box and whisker plot with outliers, Selected and peer-group layers overlaid as markers."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker


BAR_BLUE     = "#7CB9E8"
MEAN_COL     = "#E87722"
MEDIAN_COL   = "#4CAF50"
NAVY         = "#1F4E79"
ORANGE       = "#E87722"
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


def box_whisker(population_layers: list, width_emu=3429000, height_emu=3429000, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    values = [u.values[0] for u in base.units if u.values[0] is not None]
    ax.boxplot(values, vert=True, patch_artist=True, widths=0.5,
               medianprops=dict(color=MEDIAN_COL, linewidth=2 * TEXT_SCALE),
               boxprops=dict(facecolor=BAR_BLUE, color=NAVY, linewidth=1.2 * TEXT_SCALE),
               whiskerprops=dict(color=NAVY, linewidth=1.2 * TEXT_SCALE),
               capprops=dict(color=NAVY, linewidth=1.2 * TEXT_SCALE),
               flierprops=dict(marker="o", color=ORANGE, markersize=4 * TEXT_SCALE, alpha=0.7, markeredgewidth=0))
    ms = base.metric_stats[0]
    if ms.mean is not None:
        ax.axhline(ms.mean, color=MEAN_COL, linewidth=1.5 * TEXT_SCALE, linestyle="--")

    extra_handles = []
    peer_colour_idx = 0
    selected_layer = next((l for l in population_layers if l.population_label == "Selected"), None)
    selected_ids = {u.unit_id for u in selected_layer.units} if selected_layer else set()

    for layer in population_layers[1:]:
        if layer.population_label == "Selected":
            sel_units = layer.units
            if sel_units and sel_units[0].values[0] is not None:
                sv = sel_units[0].values[0]
                ax.scatter([1], [sv], color=HIGHLIGHT, zorder=7, s=80 * (TEXT_SCALE ** 2), marker="D")
                ax.axhline(sv, color=HIGHLIGHT, linewidth=1 * TEXT_SCALE, linestyle=":", zorder=5, alpha=0.6)
                extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                    markerfacecolor=HIGHLIGHT, markersize=7 * TEXT_SCALE,
                    label=f"{sel_units[0].unit_code}: {_format_number(sv, base.format_modifier)}"))
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            peer_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
            if peer_vals and selected_ids:
                sel_in_peer = next((u.values[0] for u in layer.units
                                    if u.unit_id in selected_ids
                                    and u.values[0] is not None), None)
                if sel_in_peer is not None:
                    ax.scatter([1], [sel_in_peer], color=colour, zorder=6, s=60 * (TEXT_SCALE ** 2), marker="D", alpha=0.85)
                    ax.axhline(sel_in_peer, color=colour, linewidth=0.8 * TEXT_SCALE, linestyle=":", zorder=5, alpha=0.5)
                    extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                        markerfacecolor=colour, markersize=6 * TEXT_SCALE, label=layer.population_label))

    ax.set_xticks([])
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=9 * TEXT_SCALE)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)
    ax.set_xlabel(f"n = {len(values)}", fontsize=8 * TEXT_SCALE, color="#555555")
    handles = [
        mpatches.Patch(facecolor=BAR_BLUE, edgecolor=NAVY, label="IQR"),
        plt.Line2D([0],[0], color=MEDIAN_COL, linewidth=2 * TEXT_SCALE,
                   label=f"Median: {_format_number(ms.median, base.format_modifier)}" if ms.median is not None else "Median"),
        plt.Line2D([0],[0], color=MEAN_COL, linewidth=1.5 * TEXT_SCALE, linestyle="--",
                   label=f"Mean: {_format_number(ms.mean, base.format_modifier)}" if ms.mean is not None else "Mean"),
        plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=ORANGE, markersize=5 * TEXT_SCALE, label="Outliers"),
    ] + extra_handles
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=2, fontsize=7 * TEXT_SCALE, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig)
