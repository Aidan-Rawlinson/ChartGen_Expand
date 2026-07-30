"""
donut_component.py
Base Chart — NumericCompositional. Donut chart showing component
proportions. Population layers not applicable — renders aggregated sample
averages.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width,
height, tweaks).
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


def donut_component(population_layers: list, width=55, height=55, tweaks=""):
    """Donut chart showing component proportions."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    total = sum(values) or 1
    colours = PIE_COLOURS[:len(components)]
    wedges, _, autotexts = ax.pie(
        values, colors=colours, startangle=90,
        autopct=lambda p: f"{p:.1f}%" if p > 5 else "",
        pctdistance=0.75,
        wedgeprops={"width": 0.55, "linewidth": 1.5, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(8); at.set_color("white"); at.set_fontweight("bold")
    ax.legend(wedges, [f"{c} ({v/total*100:.1f}%)" for c, v in zip(components, values)],
              loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    return _fig_to_bytes(fig)
