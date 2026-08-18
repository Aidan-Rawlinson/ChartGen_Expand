"""
line_ci_na.py
Base Chart -- TimeSeries, diagnostic variant, the "N/A" member of the
"CI" family alongside line_ci_at_least_90pct/line_ci_at_least_median/
line_ci_at_most_median/line_ci_at_most_2/line_ci_at_most_5pct/line_ci_0/
line_ci_100pct. Unlike every other member of that family, this one does
not evaluate anything -- it completely disregards population_layers and
tweaks and always draws the same thing: a single circle, sized and
positioned exactly as every other member of the family sizes its own
circle (same CIRCLE_DIAMETER_FRACTION, same centring, same default
width_emu/height_emu), with the literal text "N/A" in place of the
pass/fail/no-data tick/cross/dash mark the rest of the family draws.

Intended for rows in the Running Order where this particular evaluation
genuinely does not apply to the metric in that slot, but the row still
needs a same-sized placeholder rather than a gap or an error.

width_emu/height_emu are still respected (this is how every Base Chart's
physical output size is controlled, not part of the "data" being
disregarded) -- only population_layers and tweaks are ignored.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) -- no report_context or any other runtime object.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt

EMU_PER_INCH = 914400

CIRCLE_FILL_NA = "#C1C8CE"   # same light grey as the rest of the family's own "no_data" fill
TEXT_COLOUR = "white"

CIRCLE_DIAMETER_FRACTION = 0.72   # matches every other member of this family


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

    # Font size scaled to the circle's own radius (in points, via the
    # figure's own EMU-derived inches), the same way the rest of the
    # family scales its tick/cross/dash mark's linewidth to the circle --
    # so "N/A" sits proportionally regardless of what width_emu/
    # height_emu this row happens to specify.
    fontsize = r * 72 * 0.45
    ax.text(cx, cy, "N/A", color=TEXT_COLOUR, fontsize=fontsize,
             fontweight="bold", ha="center", va="center", zorder=2)

    return _fig_to_bytes(fig)
