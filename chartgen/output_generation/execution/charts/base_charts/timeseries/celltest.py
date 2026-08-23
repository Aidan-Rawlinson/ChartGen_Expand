"""Base Chart, diagnostic. Ignores population_layers and returns a single 50% transparent green rectangle of exactly width_emu x height_emu, to show where a chart-cell rectangle actually sits."""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

EMU_PER_INCH = 914400


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def celltest(population_layers: list = None, width_emu=2736215, height_emu=684054, tweaks=""):
    w, h = _size_to_inches(width_emu, height_emu)
    fig = plt.figure(figsize=(w, h))

    rgba = mcolors.to_rgba("green", alpha=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor=rgba, edgecolor="none",
                transparent=False)
    plt.close(fig)
    buf.seek(0)
    return buf
