"""
numeric_compositional.py
Base Chart functions for the NumericCompositional data shape: one or more
Metric-Series whose Component-Series sum to a whole (e.g. radar/spider chart
data). Population layers not applicable — charts render aggregated sample
averages.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

from core.shared.normalisation_containers.shapes import autotable_stats
from core.output_generation.execution.charts.base_charts.shared import (
    BAR_BLUE, NAVY, PIE_COLOURS,
    _size_to_inches, _fig_to_bytes, _apply_spine_style,
    _autotable_with_selection,
)


def ugly_bar(population_layers: list, width=80, height=40, tweaks=[], report_context=None):
    """Horizontal bar — component breakdown (sample average)."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    y = np.arange(len(components))
    ax.barh(y, values, color=BAR_BLUE, height=0.5, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(components, fontsize=8)
    ax.invert_yaxis()
    if base.format_modifier == "P":
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.set_xlim(0, max(values) * 1.15 if values else 100)
    ax.set_title(base.title or "", fontsize=10, fontweight="bold", pad=10)
    ax.tick_params(axis="x", labelsize=8)
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    handles = [
        mpatches.Patch(color=BAR_BLUE,  label="Sample Average"),
        mpatches.Patch(color="#AAAAAA", label="Unit"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.15),
              ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def radar_chart(population_layers: list, width=55, height=55, tweaks=[], report_context=None):
    """Radar / spider chart — component values on radial axes."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig = plt.figure(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    N = len(components)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles_plot = angles + [angles[0]]
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles_plot, values_plot, color=NAVY, linewidth=2, zorder=3)
    ax.fill(angles_plot, values_plot, color=BAR_BLUE, alpha=0.35, zorder=2)
    ax.scatter(angles, values, color=NAVY, s=40, zorder=4)
    ax.set_xticks(angles)
    labels = [c if len(c) <= 18 else c[:16] + "…" for c in components]
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.tick_params(axis="y", labelsize=7, colors="#888888")
    ax.yaxis.grid(True, color="#DDDDDD", linewidth=0.7)
    ax.xaxis.grid(True, color="#DDDDDD", linewidth=0.7)
    ax.spines["polar"].set_visible(False)
    if base.format_modifier == "P":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title(base.title or "", fontsize=10, fontweight="bold", pad=20)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def donut_component(population_layers: list, width=55, height=55, tweaks=[], report_context=None):
    """Donut chart showing component proportions."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    total = sum(values) or 1
    colours = PIE_COLOURS[:len(components)]
    wedges, _, autotexts = ax.pie(
        values, colors=colours, startangle=90,
        autopct=lambda p: f"{p:.1f}%" if p > 5 else "",
        pctdistance=0.75,
        wedgeprops={"width": 0.55, "linewidth": 1.5, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(8); at.set_color("white"); at.set_fontweight("bold")
    ax.set_title(base.title or "", fontsize=10, fontweight="bold", pad=10)
    ax.legend(wedges, [f"{c} ({v/total*100:.1f}%)" for c, v in zip(components, values)],
              loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def lollipop_chart(population_layers: list, width=70, height=40, tweaks=[], report_context=None):
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
        fmt = f"{val:.1f}%" if base.format_modifier == "P" else f"{val:g}"
        ax.text(val + max(values) * 0.02, yi, fmt, va="center", fontsize=8, color=NAVY)
    ax.set_yticks(y)
    ax.set_yticklabels(components, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.2 if values else 100)
    ax.set_title(base.title or "", fontsize=10, fontweight="bold", pad=10)
    ax.tick_params(axis="x", labelsize=8)
    if base.format_modifier == "P":
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def waffle_chart(population_layers: list, width=60, height=50, tweaks=[], report_context=None):
    """Waffle chart — 10×10 grid, each cell ≈ 1%."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    components = metric.component_names
    values = [v if v is not None else 0 for v in metric.units[0].values]
    total = sum(values) or 1
    pcts = [v / total * 100 for v in values]
    cells = []
    for i, p in enumerate(pcts):
        cells.extend([i] * round(p))
    cells = cells[:100]
    while len(cells) < 100:
        cells.append(len(components) - 1)
    colours = PIE_COLOURS[:len(components)]
    grid = np.array(cells).reshape(10, 10)
    for row in range(10):
        for col in range(10):
            cat_idx = grid[row, col]
            rect = plt.Rectangle((col, 9 - row), 0.9, 0.9,
                                  facecolor=colours[cat_idx], edgecolor="white", linewidth=1.5)
            ax.add_patch(rect)
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(base.title or "", fontsize=10, fontweight="bold", pad=10)
    handles = [mpatches.Patch(color=colours[i], label=f"{components[i]} ({pcts[i]:.1f}%)")
               for i in range(len(components))]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)
