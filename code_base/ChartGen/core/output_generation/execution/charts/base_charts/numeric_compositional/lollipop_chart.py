"""
lollipop_chart.py
Base Chart — NumericCompositional. Lollipop chart, stem and dot per
component. Population layers not applicable — renders aggregated sample
averages.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width,
height, tweaks).
"""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BAR_BLUE = "#7CB9E8"
NAVY     = "#1F4E79"

DPI = 300
NARROWER_DIM_INCHES = 7.5


def _size_to_inches(width, height):
    s = NARROWER_DIM_INCHES / 100
    return width * s, height * s


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
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


def lollipop_chart(population_layers: list, width=70, height=40, tweaks=""):
    """Lollipop chart — stem and dot per component."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    y = np.arange(len(components))
    ax.hlines(y, 0, values, color=BAR_BLUE, linewidth=2.5, zorder=2)
    ax.scatter(values, y, color=NAVY, s=80, zorder=3)
    for i, (val, yi) in enumerate(zip(values, y)):
        ax.text(val + max(values) * 0.02, yi, _format_number(val, base.format_modifier), va="center", fontsize=8, color=NAVY)
    ax.set_yticks(y)
    ax.set_yticklabels(components, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.2 if values else 100)
    ax.tick_params(axis="x", labelsize=8)
    ax.xaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    fig.tight_layout()
    return _fig_to_bytes(fig)
