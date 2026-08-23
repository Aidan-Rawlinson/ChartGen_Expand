"""Base Chart, CategoricalCompositional. Treemap, area-proportional category rectangles."""

import io
import warnings
warnings.filterwarnings("ignore")

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


def treemap(population_layers: list, width_emu=4457700, height_emu=3086100, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    categories = metric.category_names
    counts = metric.stats.component_counts
    total = sum(c for c in counts if c is not None) or 1
    pcts = [c / total * 100 for c in counts]
    colours = PIE_COLOURS[:len(categories)]
    sorted_items = sorted(zip(pcts, categories, colours), reverse=True)
    x_cursor = 0
    for pct, cat, col in sorted_items:
        bw = pct / 100
        rect = plt.Rectangle((x_cursor, 0), bw, 1.0,
                              facecolor=col, edgecolor="white", linewidth=2 * TEXT_SCALE)
        ax.add_patch(rect)
        cx, cy = x_cursor + bw / 2, 0.5
        if bw > 0.06:
            ax.text(cx, cy + 0.15, cat, ha="center", va="center",
                    fontsize=8 * TEXT_SCALE, color="white", fontweight="bold")
            ax.text(cx, cy - 0.15, f"{pct:.1f}%", ha="center", va="center",
                    fontsize=8 * TEXT_SCALE, color="white")
        x_cursor += bw
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.tight_layout()
    return _fig_to_bytes(fig)
