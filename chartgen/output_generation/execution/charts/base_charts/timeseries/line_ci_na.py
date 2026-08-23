"""Base Chart, TimeSeries, diagnostic. The N/A member of the line_ci_* family. Evaluates nothing and always draws a circle with the literal text N/A, sized as the rest of the family."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt

EMU_PER_INCH = 914400

CIRCLE_FILL_NA = "#C1C8CE"
TEXT_COLOUR = "white"

CIRCLE_DIAMETER_FRACTION = 0.72


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor="none", edgecolor="none",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def line_ci_na(population_layers: list, width_emu=2736215, height_emu=684054, tweaks=""):
    w_in, h_in = _size_to_inches(width_emu, height_emu)

    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.axis("off")

    cx, cy = w_in / 2, h_in / 2
    r = (min(w_in, h_in) / 2) * CIRCLE_DIAMETER_FRACTION

    circle = plt.Circle((cx, cy), r, facecolor=CIRCLE_FILL_NA, edgecolor="none", zorder=1)
    ax.add_patch(circle)

    # Derived from the circle radius, so already inflated with the
    # canvas. A TEXT_SCALE here would double-apply.
    fontsize = r * 72 * 0.45
    ax.text(cx, cy, "N/A", color=TEXT_COLOUR, fontsize=fontsize,
             fontweight="bold", ha="center", va="center", zorder=2)

    return _fig_to_bytes(fig)
