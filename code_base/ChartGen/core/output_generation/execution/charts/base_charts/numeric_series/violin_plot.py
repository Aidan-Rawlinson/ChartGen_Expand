"""
violin_plot.py
Base Chart — NumericSeries. Violin / KDE distribution plot; the Selected
unit and any peer-group layers overlaid as markers.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width,
height, tweaks) — no report_context or any other runtime object. The
Selected unit's identity and label come entirely from the
"Selected"-labelled entry in population_layers.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font, baked into the SVG
# vector output as real glyph outlines (svg.fonttype default "path").
# See Architecture, SVG rendering methodology.
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Palette / sizing / formatting — inlined, this chart's own copy
# ---------------------------------------------------------------------------

BAR_BLUE     = "#7CB9E8"
MEAN_COL     = "#E87722"
MEDIAN_COL   = "#4CAF50"
NAVY         = "#1F4E79"
HIGHLIGHT    = "#C12958"
PEER_COLOURS = ["#2E9E75", "#7030A0", "#E87722", "#2E86AB"]

NARROWER_DIM_INCHES = 7.5


def _size_to_inches(width, height):
    s = NARROWER_DIM_INCHES / 100
    return width * s, height * s


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


def violin_plot(population_layers: list, width=50, height=50, tweaks=""):
    """Violin plot — distribution from first shape, markers for subsequent layers."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    values = [u.values[0] for u in base.units if u.values[0] is not None]
    parts = ax.violinplot(values, vert=True, showmedians=True, showextrema=True)
    for pc in parts["bodies"]:
        pc.set_facecolor(BAR_BLUE); pc.set_edgecolor(NAVY); pc.set_alpha(0.75)
    parts["cmedians"].set_color(MEDIAN_COL); parts["cmedians"].set_linewidth(2)
    parts["cmaxes"].set_color(NAVY); parts["cmins"].set_color(NAVY); parts["cbars"].set_color(NAVY)
    ms = base.metric_stats[0]
    if ms.mean is not None:
        ax.scatter([1], [ms.mean], color=MEAN_COL, zorder=5, s=50)

    extra_handles = []
    peer_colour_idx = 0
    # Identity of the currently Selected unit(s), for matching within peer
    # layers below — sourced from the "Selected" population layer itself,
    # not from any external runtime object.
    selected_layer = next((l for l in population_layers if l.population_label == "Selected"), None)
    selected_ids = {u.unit_id for u in selected_layer.units} if selected_layer else set()

    for layer in population_layers[1:]:
        if layer.population_label == "Selected":
            sel_units = [u for u in layer.units if u.values[0] is not None]
            if sel_units:
                sv = sel_units[0].values[0]
                ax.scatter([1], [sv], color=HIGHLIGHT, zorder=7, s=80, marker="D")
                ax.axhline(sv, color=HIGHLIGHT, linewidth=1, linestyle=":", zorder=5, alpha=0.6)
                extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                    markerfacecolor=HIGHLIGHT, markersize=7,
                    label=f"{sel_units[0].unit_code}: {_format_number(sv, base.format_modifier)}"))
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            if selected_ids:
                sel_in_peer = next((u.values[0] for u in layer.units
                                    if u.unit_id in selected_ids
                                    and u.values[0] is not None), None)
                if sel_in_peer is not None:
                    ax.scatter([1], [sel_in_peer], color=colour, zorder=6, s=60, marker="D", alpha=0.85)
                    ax.axhline(sel_in_peer, color=colour, linewidth=0.8, linestyle=":", zorder=5, alpha=0.5)
                    extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                        markerfacecolor=colour, markersize=6, label=layer.population_label))

    ax.set_xticks([])
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=9)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.set_xlabel(f"n = {len(values)}", fontsize=8, color="#555555")
    handles = [
        mpatches.Patch(facecolor=BAR_BLUE, edgecolor=NAVY, alpha=0.75, label="Distribution"),
        plt.Line2D([0],[0], color=MEDIAN_COL, linewidth=2,
                   label=f"Median: {_format_number(ms.median, base.format_modifier)}" if ms.median is not None else "Median"),
        plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=MEAN_COL, markersize=6,
                   label=f"Mean: {_format_number(ms.mean, base.format_modifier)}" if ms.mean is not None else "Mean"),
    ] + extra_handles
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig)
