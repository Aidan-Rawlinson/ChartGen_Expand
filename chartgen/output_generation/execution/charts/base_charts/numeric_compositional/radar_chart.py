"""Base Chart, NumericCompositional. Radar chart of component values on radial axes."""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BAR_BLUE = "#7CB9E8"
NAVY     = "#1F4E79"

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


def _format_number(value, format_modifier):
    if value is None:
        return ""
    if format_modifier == "P":
        return f"{value:,.0f}%"
    if format_modifier == "C":
        return f"£{value:,.0f}"
    return f"{value:,.0f}"


def _axis_formatter(format_modifier):
    return mticker.FuncFormatter(lambda v, _: _format_number(v, format_modifier))


def radar_chart(population_layers: list, width_emu=3771900, height_emu=3771900, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig = plt.figure(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    N = len(components)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles_plot, values_plot, color=NAVY, linewidth=2 * TEXT_SCALE, zorder=3)
    ax.fill(angles_plot, values_plot, color=BAR_BLUE, alpha=0.35, zorder=2)
    ax.scatter(angles, values, color=NAVY, s=40 * (TEXT_SCALE ** 2), zorder=4)
    ax.set_xticks(angles)
    labels = [c if len(c) <= 18 else c[:16] + "…" for c in components]
    ax.set_xticklabels(labels, fontsize=7.5 * TEXT_SCALE)
    ax.tick_params(axis="y", labelsize=7 * TEXT_SCALE, colors="#888888")
    ax.yaxis.grid(True, color="#DDDDDD", linewidth=0.7 * TEXT_SCALE)
    ax.xaxis.grid(True, color="#DDDDDD", linewidth=0.7 * TEXT_SCALE)
    ax.spines["polar"].set_visible(False)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    fig.tight_layout()
    return _fig_to_bytes(fig)
