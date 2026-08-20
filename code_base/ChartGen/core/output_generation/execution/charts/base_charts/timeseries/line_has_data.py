"""
line_has_data.py
Base Chart -- TimeSeries, diagnostic variant. Not a line chart in the
sense of plotting values -- a single positive/negative indicator for
whether the Selected unit's own submission has any data at all for this
metric: a grey circle with a white tick (positive -- at least one
non-None value present) or a white cross (negative -- no submission
unit found, or every value is None).

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) -- no report_context or any other runtime object.

"Any data" is deliberately looser than sparkline1's own has_submission
guard (which requires every value non-None before it will draw a
submission line at all) -- this chart's whole purpose is to flag
partial/incomplete data as still present, not to decide whether it's
safe to plot a continuous line through it.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font, though this chart draws
# no text; kept for consistency with every other Base Chart. SVG text is
# kept as real text, not glyph outlines (see line_ci_full's own comment
# for the full reasoning) -- irrelevant here with no text, but harmless
# and kept consistent with every other Base Chart.
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt

EMU_PER_INCH = 914400

GREY_FILL = "#C1C8CE"  # three hops lighter than the original #9AA5AF (each hop ~15% toward white)
MARK_COLOUR = "white"

# Circle diameter as a fraction of the smaller canvas dimension -- leaves
# a margin on all sides so the circle never touches the canvas edge.
# 0.72 = 90% of the original 0.8.
CIRCLE_DIAMETER_FRACTION = 0.72


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    # No bbox_inches="tight" -- the returned SVG must be exactly
    # width_emu x height_emu; everything here is drawn well within the
    # canvas (see CIRCLE_DIAMETER_FRACTION's own margin), so nothing is
    # ever at risk of being cropped off by skipping the crop.
    fig.savefig(buf, format="svg", facecolor="none", edgecolor="none",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _has_submission_data(population_layers):
    """True if the Selected layer's own submission unit has at least one
    non-None value -- "any data", not "complete data" (see module
    docstring)."""
    for layer in population_layers[1:] if population_layers else []:
        if getattr(layer, "population_label", None) != "Selected":
            continue
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        unit = layer_metric.units[0] if layer_metric.units else None
        if unit is not None and unit.values and any(v is not None for v in unit.values):
            return True
    return False


def line_has_data(population_layers: list, width_emu=2736215, height_emu=684054, tweaks=""):
    w_in, h_in = _size_to_inches(width_emu, height_emu)

    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_position([0, 0, 1, 1])
    # Data coordinates set to exactly 1 unit == 1 inch, in both directions
    # -- since the axes fill the entire figure canvas ([0,0,1,1]) and the
    # data limits match the figure's own physical width/height exactly, a
    # circle of a given radius in these units comes out truly circular
    # regardless of the canvas's own aspect ratio (a wide table cell,
    # say), with no separate aspect-ratio correction needed.
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.axis("off")

    cx, cy = w_in / 2, h_in / 2
    r = (min(w_in, h_in) / 2) * CIRCLE_DIAMETER_FRACTION

    circle = plt.Circle((cx, cy), r, facecolor=GREY_FILL, edgecolor="none", zorder=1)
    ax.add_patch(circle)

    lw = max(1.2, r * 72 * 0.12)  # linewidth in points, scaled to the circle's own size

    if _has_submission_data(population_layers):
        # Tick: two segments, short-then-long, classic checkmark
        # proportions, scaled by r and centred on (cx, cy).
        p1 = (cx - 0.5 * r, cy - 0.05 * r)
        p2 = (cx - 0.1 * r, cy - 0.45 * r)
        p3 = (cx + 0.55 * r, cy + 0.45 * r)
        ax.plot([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round",
                solid_joinstyle="round", zorder=2)
    else:
        # Cross: two crossing diagonals.
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy - 0.4 * r, cy + 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy + 0.4 * r, cy - 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)

    return _fig_to_bytes(fig)
