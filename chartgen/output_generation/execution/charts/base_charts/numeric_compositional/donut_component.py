"""Base Chart, NumericCompositional. Donut chart showing component proportions."""

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


def donut_component(population_layers: list, width_emu=3771900, height_emu=3771900, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
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
        wedgeprops={"width": 0.55, "linewidth": 1.5 * TEXT_SCALE, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(8 * TEXT_SCALE); at.set_color("white"); at.set_fontweight("bold")
    ax.legend(wedges, [f"{c} ({v/total*100:.1f}%)" for c, v in zip(components, values)],
              loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=7 * TEXT_SCALE, frameon=False, ncol=2)
    fig.tight_layout()
    return _fig_to_bytes(fig)
