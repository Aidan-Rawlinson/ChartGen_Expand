"""Base Chart, CategoricalCompositional. Diverging bar, Yes right and No left from a centre axis."""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

YES_COL = "#4CAF50"
NO_COL  = "#C0392B"

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


def diverging_bar(population_layers: list, width_emu=5486400, height_emu=3771900, tweaks=""):
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
    ax.barh(y,  yes_pcts,              color=YES_COL, height=0.55, zorder=2)
    ax.barh(y, [-n for n in no_pcts],  color=NO_COL,  height=0.55, zorder=2)
    ax.axvline(0, color="#333333", linewidth=0.8 * TEXT_SCALE, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(questions, fontsize=7 * TEXT_SCALE)
    ax.invert_yaxis()
    lim = max(max(yes_pcts), max(no_pcts)) * 1.1
    ax.set_xlim(-lim, lim)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{abs(v):.0f}%"))
    ax.tick_params(axis="x", labelsize=7 * TEXT_SCALE)
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)
    ax.text( lim * 0.5,  -0.8, "Yes →", ha="center", va="center", fontsize=8 * TEXT_SCALE, color=YES_COL, fontweight="bold")
    ax.text(-lim * 0.5,  -0.8, "← No",  ha="center", va="center", fontsize=8 * TEXT_SCALE, color=NO_COL,  fontweight="bold")
    fig.tight_layout()
    return _fig_to_bytes(fig)
