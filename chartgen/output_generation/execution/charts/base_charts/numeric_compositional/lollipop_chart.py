"""Base Chart, NumericCompositional. Lollipop chart, stem and dot per component."""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

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


def _apply_spine_style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


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


def lollipop_chart(population_layers: list, width_emu=4800600, height_emu=2743200, tweaks=""):
    base = population_layers[0]
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    y = np.arange(len(components))
    ax.hlines(y, 0, values, color=BAR_BLUE, linewidth=2.5 * TEXT_SCALE, zorder=2)
    ax.scatter(values, y, color=NAVY, s=80 * (TEXT_SCALE ** 2), zorder=3)
    for i, (val, yi) in enumerate(zip(values, y)):
        ax.text(val + max(values) * 0.02, yi, _format_number(val, base.format_modifier), va="center", fontsize=8 * TEXT_SCALE, color=NAVY)
    ax.set_yticks(y)
    ax.set_yticklabels(components, fontsize=8 * TEXT_SCALE)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.2 if values else 100)
    ax.tick_params(axis="x", labelsize=8 * TEXT_SCALE)
    ax.xaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7 * TEXT_SCALE)
    _apply_spine_style(ax)
    fig.tight_layout()
    return _fig_to_bytes(fig)
