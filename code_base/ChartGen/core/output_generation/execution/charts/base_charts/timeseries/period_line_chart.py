"""
period_line_chart.py
Base Chart — TimeSeries. Population mean/IQR band across every period,
with a highlighted line per subsequent population layer (Selected or peer
group).

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) — no report_context or any other runtime object. The
Selected unit's label comes from its own unit_code in the
"Selected"-labelled population layer.

population_layers[0] is always the scope and drives the main rendering
(population mean line, IQR band), regardless of its own label;
population_layers[1:] are highlighted on top — "Selected" as the
individual unit's own trend line, any other label (a resolved peer group)
as that group's mean line, in PEER_COLOURS order.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font. SVG text is kept as
# real text, not glyph outlines -- see line_ci_full's own comment for
# the full reasoning.
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BAR_BLUE     = "#7CB9E8"
MEAN_COL     = "#E87722"
HIGHLIGHT    = "#C12958"
PEER_COLOURS = ["#2E9E75", "#7030A0", "#E87722", "#2E86AB"]

EMU_PER_INCH = 914400

# PowerPoint SVG-text-compression workaround -- see line_ci_full's own
# TEXT_SCALE comment for the full reasoning. Must match the system
# layer's own CHART_RENDER_SCALE (assembly_engine.py) exactly.
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


def period_line_chart(population_layers: list, width_emu=5486400, height_emu=3086100, tweaks=""):
    """Line chart of one Metric-Series across every period — population mean/IQR band, plus a highlighted line per subsequent layer (Selected or peer group)."""
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

    means = [ps.mean for ps in metric.period_stats]
    ax.plot(x, means, color=MEAN_COL, linewidth=2 * TEXT_SCALE, zorder=2, label="Population mean")
    q1 = [ps.q1 for ps in metric.period_stats]
    q3 = [ps.q3 for ps in metric.period_stats]
    if q1 and q3 and all(v is not None for v in q1) and all(v is not None for v in q3):
        ax.fill_between(x, q1, q3, color=BAR_BLUE, alpha=0.25, zorder=1, label="IQR")

    peer_colour_idx = 0
    for layer in population_layers[1:]:
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        if layer.population_label == "Selected":
            unit = layer_metric.units[0] if layer_metric.units else None
            if unit is not None:
                ax.plot(x, unit.values, color=HIGHLIGHT, linewidth=2 * TEXT_SCALE, marker="o",
                        markersize=4 * TEXT_SCALE, zorder=4, label=unit.unit_code)
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            peer_means = [ps.mean for ps in layer_metric.period_stats]
            ax.plot(x, peer_means, color=colour, linewidth=1.5 * TEXT_SCALE, linestyle="--", zorder=3,
                    label=layer.population_label)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7 * TEXT_SCALE)
    ax.tick_params(axis="y", labelsize=8 * TEXT_SCALE)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7 * TEXT_SCALE, frameon=False)
    fig.tight_layout()

    return _fig_to_bytes(fig)
