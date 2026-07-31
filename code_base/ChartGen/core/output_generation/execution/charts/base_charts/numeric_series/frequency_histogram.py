"""
frequency_histogram.py
Base Chart — NumericSeries. Frequency histogram with mean/median reference
lines; the Selected unit and any peer-group layers overlaid as vertical
lines.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) — no report_context or any other runtime object. The
Selected unit's identity and label come entirely from the
"Selected"-labelled entry in population_layers.
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

# ---------------------------------------------------------------------------
# Palette / sizing / formatting — inlined, this chart's own copy
# ---------------------------------------------------------------------------

BAR_BLUE     = "#7CB9E8"
MEAN_COL     = "#E87722"
MEDIAN_COL   = "#4CAF50"
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


def frequency_histogram(population_layers: list, width_emu=4114800, height_emu=3086100, tweaks=""):
    """Frequency histogram — distribution from first shape, reference lines for subsequent layers."""
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    values = [u.values[0] for u in base.units if u.values[0] is not None]
    n_bins = min(max(int(np.sqrt(len(values))), 8), 20)
    ax.hist(values, bins=n_bins, color=BAR_BLUE, edgecolor="white", linewidth=0.8, zorder=2)
    ms = base.metric_stats[0]
    if ms.mean   is not None: ax.axvline(ms.mean,   color=MEAN_COL,   linewidth=1.5, label=f"Mean: {_format_number(ms.mean, base.format_modifier)}")
    if ms.median is not None: ax.axvline(ms.median, color=MEDIAN_COL, linewidth=1.5, label=f"Median: {_format_number(ms.median, base.format_modifier)}")

    peer_colour_idx = 0
    for layer in population_layers[1:]:
        if layer.population_label == "Selected":
            sel_units = [u for u in layer.units if u.values[0] is not None]
            if sel_units:
                sv = sel_units[0].values[0]
                ax.axvline(sv, color=HIGHLIGHT, linewidth=2, linestyle="--", zorder=4,
                           label=f"{sel_units[0].unit_code}: {_format_number(sv, base.format_modifier)}")
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            peer_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
            if peer_vals:
                peer_mean = float(np.mean(peer_vals))
                ax.axvline(peer_mean, color=colour, linewidth=1.5, linestyle="--",
                           label=f"{layer.population_label} mean: {_format_number(peer_mean, base.format_modifier)}")

    ax.xaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(labelsize=8)
    ax.set_ylabel("Count", fontsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig)
