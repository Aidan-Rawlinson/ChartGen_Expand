"""
celltest.py
Base Chart -- diagnostic, not tied to any data shape. Ignores
population_layers entirely; returns a single rectangle exactly
width_emu x height_emu, filled with a 50% transparent green. Exists
purely to show where a chart-cell rectangle actually sits and how big it
actually is once spliced into a table or inserted into a report -- there
is no data to plot, so any mismatch visible is the cell geometry itself,
not a rendering quirk of a real chart.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) -- population_layers and tweaks are accepted but
unused, kept for signature parity with every other Base Chart.
"""

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

    # 50% transparent green, filling the entire figure -- no axes, no
    # margins, nothing else drawn. facecolor carries the alpha; transparent
    # is explicitly False so that alpha is honoured rather than overridden
    # to fully transparent.
    rgba = mcolors.to_rgba("green", alpha=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor=rgba, edgecolor="none",
                transparent=False)
    plt.close(fig)
    buf.seek(0)
    return buf
