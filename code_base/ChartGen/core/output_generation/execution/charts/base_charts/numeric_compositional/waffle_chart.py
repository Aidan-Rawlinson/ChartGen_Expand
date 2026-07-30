"""
waffle_chart.py
Base Chart — NumericCompositional. Waffle chart, 10x10 grid, each cell
approx. 1%. Population layers not applicable — renders aggregated sample
averages.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width,
height, tweaks).
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

PIE_COLOURS = ["#1F4E79", "#E87722", "#7030A0", "#2E86AB", "#F0A500", "#4CAF50"]

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


def waffle_chart(population_layers: list, width=60, height=50, tweaks=""):
    """Waffle chart — 10×10 grid, each cell ≈ 1%."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    total = sum(values) or 1
    pcts = [v / total * 100 for v in values]
    cells = []
    for i, p in enumerate(pcts):
        cells.extend([i] * round(p))
    cells = cells[:100]
    while len(cells) < 100:
        cells.append(len(components) - 1)
    colours = PIE_COLOURS[:len(components)]
    grid = np.array(cells).reshape(10, 10)
    for row in range(10):
        for col in range(10):
            cat_idx = grid[row, col]
            rect = plt.Rectangle((col, 9 - row), 0.9, 0.9,
                                  facecolor=colours[cat_idx], edgecolor="white", linewidth=1.5)
            ax.add_patch(rect)
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_aspect("equal"); ax.axis("off")
    handles = [mpatches.Patch(color=colours[i], label=f"{components[i]} ({pcts[i]:.1f}%)")
               for i in range(len(components))]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    return _fig_to_bytes(fig)
