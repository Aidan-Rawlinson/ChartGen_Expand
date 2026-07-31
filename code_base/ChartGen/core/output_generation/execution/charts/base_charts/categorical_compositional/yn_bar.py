"""
yn_bar.py
Base Chart — CategoricalCompositional. Horizontal stacked Yes/No bar per
question. Population layers not applicable — renders population-level
aggregates.

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

# Calibri -- ChartGen's standard chart/table font, baked into the SVG
# vector output as real glyph outlines (svg.fonttype default "path").
# See Architecture, SVG rendering methodology.
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

YES_COL = "#4CAF50"
NO_COL  = "#C0392B"

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


def yn_bar(population_layers: list, width_emu=5486400, height_emu=3771900, tweaks=""):
    """Horizontal stacked Yes/No bar per question."""
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    questions, yes_pcts, no_pcts = [], [], []
    for metric in base.metrics:
        total = metric.stats.count_with_data or 1
        counts = metric.stats.component_counts
        yes_pcts.append((counts[0] / total * 100) if len(counts) > 0 else 0)
        no_pcts.append( (counts[1] / total * 100) if len(counts) > 1 else 0)
        questions.append(metric.name or "")
    y = np.arange(len(questions))
    ax.barh(y, yes_pcts, color=YES_COL, height=0.5, zorder=2)
    ax.barh(y, no_pcts,  color=NO_COL,  height=0.5, left=yes_pcts, zorder=2)
    ax.set_yticks(y); ax.set_yticklabels(questions, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.xaxis.tick_top(); ax.xaxis.set_label_position("top")
    ax.tick_params(axis="x", labelsize=7)
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    ax.spines["bottom"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)
    handles = [mpatches.Patch(color=YES_COL, label="Yes"), mpatches.Patch(color=NO_COL, label="No")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.03),
              ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig)
