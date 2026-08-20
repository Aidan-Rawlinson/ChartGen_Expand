"""
ugly_bar.py
Base Chart — NumericCompositional. Horizontal bar showing component
breakdown (sample average). Population layers not applicable — renders
aggregated sample averages.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks).
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
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

BAR_BLUE = "#7CB9E8"

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


def ugly_bar(population_layers: list, width_emu=5486400, height_emu=2743200, tweaks=""):
    """Horizontal bar — component breakdown (sample average)."""
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    y = np.arange(len(components))
    ax.barh(y, values, color=BAR_BLUE, height=0.5, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(components, fontsize=8 * TEXT_SCALE)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    if base.format_modifier == "P":
        ax.set_xlim(0, max(values) * 1.15 if values else 100)
    ax.tick_params(axis="x", labelsize=8 * TEXT_SCALE)
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)
    handles = [
        mpatches.Patch(color=BAR_BLUE,  label="Sample Average"),
        mpatches.Patch(color="#AAAAAA", label="Unit"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.15),
              ncol=2, fontsize=7 * TEXT_SCALE, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig)
