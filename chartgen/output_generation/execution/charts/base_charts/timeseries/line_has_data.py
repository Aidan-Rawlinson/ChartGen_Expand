"""Base Chart, TimeSeries, diagnostic. A grey circle with a white tick if the Selected unit has any non-None value for this metric, a white cross if not."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt

EMU_PER_INCH = 914400

GREY_FILL = "#C1C8CE"
MARK_COLOUR = "white"

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


def _has_submission_data(population_layers):
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
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.axis("off")

    cx, cy = w_in / 2, h_in / 2
    r = (min(w_in, h_in) / 2) * CIRCLE_DIAMETER_FRACTION

    circle = plt.Circle((cx, cy), r, facecolor=GREY_FILL, edgecolor="none", zorder=1)
    ax.add_patch(circle)

    lw = max(1.2, r * 72 * 0.12)

    if _has_submission_data(population_layers):
        p1 = (cx - 0.5 * r, cy - 0.05 * r)
        p2 = (cx - 0.1 * r, cy - 0.45 * r)
        p3 = (cx + 0.55 * r, cy + 0.45 * r)
        ax.plot([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round",
                solid_joinstyle="round", zorder=2)
    else:
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy - 0.4 * r, cy + 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy + 0.4 * r, cy - 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)

    return _fig_to_bytes(fig)
