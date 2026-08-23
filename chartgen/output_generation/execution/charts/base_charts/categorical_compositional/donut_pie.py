"""Base Chart, CategoricalCompositional. Donut ring chart."""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt

PIE_COLOURS = ["#1F4E79", "#E87722", "#7030A0", "#2E86AB", "#F0A500", "#4CAF50"]

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


def donut_pie(population_layers: list, width_emu=3429000, height_emu=3771900, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    categories = metric.category_names
    counts = metric.stats.component_counts
    total = sum(c for c in counts if c is not None)
    if total == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes, fontsize=10 * TEXT_SCALE)
        return _fig_to_bytes(fig)
    pcts = [c / total * 100 for c in counts]
    colours = PIE_COLOURS[:len(categories)]
    wedges, _ = ax.pie(pcts, colors=colours, startangle=90,
                        wedgeprops={"width": 0.5, "linewidth": 2 * TEXT_SCALE, "edgecolor": "white"})
    for wedge, cat, pct in zip(wedges, categories, pcts):
        angle = (wedge.theta1 + wedge.theta2) / 2
        rad = np.radians(angle)
        x_o, y_o = 1.22 * np.cos(rad), 1.22 * np.sin(rad)
        ax.annotate(f"{cat}\n{pct:.1f}%", xy=(0.88*np.cos(rad), 0.88*np.sin(rad)),
                    xytext=(x_o, y_o), fontsize=7.5 * TEXT_SCALE,
                    ha="left" if x_o > 0 else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color="#AAAAAA", lw=0.6 * TEXT_SCALE))
    fig.tight_layout()
    return _fig_to_bytes(fig)
