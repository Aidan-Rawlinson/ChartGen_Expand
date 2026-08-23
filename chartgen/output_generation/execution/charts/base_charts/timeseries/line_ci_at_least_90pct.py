"""Base Chart, TimeSeries, diagnostic. Three-way circle indicator on the Selected unit's final-period value only: blue tick passes if the value is at least 90, orange cross fails, grey dash if there is no value."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt

EMU_PER_INCH = 914400

CIRCLE_FILL_PASS = "#7CB9E8"
CIRCLE_FILL_FAIL = "#E8AB7C"
CIRCLE_FILL_NO_DATA = "#C1C8CE"
MARK_COLOUR = "white"

CIRCLE_DIAMETER_FRACTION = 0.72

THRESHOLD = 90
EPSILON = 0.0001


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor="none", edgecolor="none",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _final_submission_value(population_layers):
    for layer in population_layers[1:] if population_layers else []:
        if getattr(layer, "population_label", None) != "Selected":
            continue
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        unit = layer_metric.units[0] if layer_metric.units else None
        if unit is not None and unit.values:
            return unit.values[-1]
    return None


def _draw_mark(ax, cx, cy, r, result):
    lw = max(1.2, r * 72 * 0.12)
    if result == "pass":
        p1 = (cx - 0.5 * r, cy - 0.05 * r)
        p2 = (cx - 0.1 * r, cy - 0.45 * r)
        p3 = (cx + 0.55 * r, cy + 0.45 * r)
        ax.plot([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round",
                solid_joinstyle="round", zorder=2)
    elif result == "fail":
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy - 0.4 * r, cy + 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy + 0.4 * r, cy - 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)
    else:
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy, cy],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)


def line_ci_at_least_90pct(population_layers: list, width_emu=2736215, height_emu=684054, tweaks=""):
    w_in, h_in = _size_to_inches(width_emu, height_emu)

    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.axis("off")

    cx, cy = w_in / 2, h_in / 2
    r = (min(w_in, h_in) / 2) * CIRCLE_DIAMETER_FRACTION

    final_value = _final_submission_value(population_layers)

    if final_value is None:
        result = "no_data"
    elif (final_value + EPSILON) >= THRESHOLD:
        result = "pass"
    else:
        result = "fail"

    circle_fill = {"pass": CIRCLE_FILL_PASS, "fail": CIRCLE_FILL_FAIL,
                   "no_data": CIRCLE_FILL_NO_DATA}[result]
    circle = plt.Circle((cx, cy), r, facecolor=circle_fill, edgecolor="none", zorder=1)
    ax.add_patch(circle)

    _draw_mark(ax, cx, cy, r, result)

    return _fig_to_bytes(fig)
