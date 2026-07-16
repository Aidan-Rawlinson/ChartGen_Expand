"""
categorical_compositional.py
Base Chart functions for the CategoricalCompositional data shape: one or
more Metric-Series (questions) with categorical Component-Series summing to
a whole (e.g. yes/no, ethnicity breakdown). Population layers not
applicable — charts render population-level aggregates.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

from core.shared.normalisation_containers.shapes import autotable_stats
from core.output_generation.execution.charts.base_charts.shared import (
    YES_COL, NO_COL, PIE_COLOURS,
    _size_to_inches, _fig_to_bytes, _apply_spine_style,
    _autotable_with_selection,
)


def yn_bar(population_layers: list, width=80, height=55, tweaks=[], report_context=None):
    """Horizontal stacked Yes/No bar per question."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    questions, yes_pcts, no_pcts = [], [], []
    for metric in base.metrics:
        total = metric.stats.count_with_data or 1
        counts = metric.stats.component_counts
        yes_pcts.append((counts[0] / total * 100) if len(counts) > 0 else 0)
        no_pcts.append( (counts[1] / total * 100) if len(counts) > 1 else 0)
        questions.append(metric.name or "")
    y = np.arange(len(questions))
    ax.barh(y, yes_pcts, color=YES_COL, height=0.5, zorder=2)
    ax.barh(y, no_pcts,  color=NO_COL,  height=0.5, left=yes_pcts, zorder=2)
    ax.set_yticks(y); ax.set_yticklabels(questions, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.xaxis.tick_top(); ax.xaxis.set_label_position("top")
    ax.tick_params(axis="x", labelsize=7)
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    ax.spines["bottom"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)
    handles = [mpatches.Patch(color=YES_COL, label="Yes"), mpatches.Patch(color=NO_COL, label="No")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.03),
              ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def list_pie(population_layers: list, width=50, height=55, tweaks=[], report_context=None):
    """Pie chart — category proportions for a single metric."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    categories = metric.category_names
    counts = metric.stats.component_counts
    total = sum(c for c in counts if c is not None)
    if total == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)
    pcts = [c / total * 100 for c in counts]
    colours = PIE_COLOURS[:len(categories)]
    wedges, _, autotexts = ax.pie(pcts, colors=colours, startangle=90,
                                   autopct=lambda p: f"{p:.1f}%" if p > 4 else "",
                                   pctdistance=0.65,
                                   wedgeprops={"linewidth": 1.5, "edgecolor": "white"})
    for at in autotexts:
        at.set_fontsize(8); at.set_color("white"); at.set_fontweight("bold")
    for wedge, cat, pct in zip(wedges, categories, pcts):
        angle = (wedge.theta1 + wedge.theta2) / 2
        rad = np.radians(angle)
        x_i, y_i = 1.05 * np.cos(rad), 1.05 * np.sin(rad)
        x_o, y_o = 1.28 * np.cos(rad), 1.28 * np.sin(rad)
        ax.annotate(f"{cat}: {pct:.1f}%", xy=(x_i, y_i), xytext=(x_o, y_o),
                    fontsize=7.5, ha="left" if x_o > 0 else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color="#888888", lw=0.8))
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def diverging_bar(population_layers: list, width=80, height=55, tweaks=[], report_context=None):
    """Diverging bar — Yes right / No left from centre axis."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    questions, yes_pcts, no_pcts = [], [], []
    for metric in base.metrics:
        total = metric.stats.count_with_data or 1
        counts = metric.stats.component_counts
        yes_pcts.append((counts[0] / total * 100) if len(counts) > 0 else 0)
        no_pcts.append( (counts[1] / total * 100) if len(counts) > 1 else 0)
        questions.append(metric.name or "")
    y = np.arange(len(questions))
    ax.barh(y,  yes_pcts,              color=YES_COL, height=0.55, zorder=2)
    ax.barh(y, [-n for n in no_pcts],  color=NO_COL,  height=0.55, zorder=2)
    ax.axvline(0, color="#333333", linewidth=0.8, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(questions, fontsize=7)
    ax.invert_yaxis()
    lim = max(max(yes_pcts), max(no_pcts)) * 1.1
    ax.set_xlim(-lim, lim)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{abs(v):.0f}%"))
    ax.tick_params(axis="x", labelsize=7)
    ax.xaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.text( lim * 0.5,  -0.8, "Yes →", ha="center", va="center", fontsize=8, color=YES_COL, fontweight="bold")
    ax.text(-lim * 0.5,  -0.8, "← No",  ha="center", va="center", fontsize=8, color=NO_COL,  fontweight="bold")
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def dot_matrix(population_layers: list, width=80, height=55, tweaks=[], report_context=None):
    """Dot matrix — filled dots per category per question, each dot ≈ 10%."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    is_yn = (len(base.metrics) > 1 and
             base.metrics[0].category_names == ["Yes", "No"])
    if is_yn:
        metrics = base.metrics
        categories = ["Yes", "No"]
        counts_list = [m.stats.component_counts for m in metrics]
        totals = [m.stats.count_with_data or 1 for m in metrics]
        questions = [m.name or "" for m in metrics]
    else:
        metric = base.metrics[0]
        categories = metric.category_names
        counts_list = [metric.stats.component_counts]
        totals = [metric.stats.count_with_data or 1]
        questions = [metric.name or ""]

    n_q = len(questions)
    n_c = len(categories)
    fig, ax = plt.subplots(figsize=(w, h))
    colours_use = [YES_COL, NO_COL] if is_yn else PIE_COLOURS[:n_c]

    for qi, (q, counts, total) in enumerate(zip(questions, counts_list, totals)):
        pcts = [(c / total * 100) if c else 0 for c in counts]
        for ci, (cat, pct, col) in enumerate(zip(categories, pcts, colours_use)):
            n_filled = round(pct / 10)
            for d in range(10):
                filled = d < n_filled
                ax.scatter(ci * 11 + d, qi,
                           s=55, color=col if filled else "#E0E0E0",
                           zorder=2, linewidths=0)

    ax.set_yticks(range(n_q)); ax.set_yticklabels(questions, fontsize=7)
    ax.invert_yaxis()
    ax.set_xticks([ci * 11 + 4.5 for ci in range(n_c)])
    ax.set_xticklabels(categories, fontsize=8, fontweight="bold")
    ax.tick_params(bottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(False); ax.set_facecolor("white")
    ax.text(0, n_q + 0.3, "Each dot ≈ 10%", fontsize=6.5, color="#888888", style="italic")
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def donut_pie(population_layers: list, width=50, height=55, tweaks=[], report_context=None):
    """Donut ring chart."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    categories = metric.category_names
    counts = metric.stats.component_counts
    total = sum(c for c in counts if c is not None)
    if total == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)
    pcts = [c / total * 100 for c in counts]
    colours = PIE_COLOURS[:len(categories)]
    wedges, _ = ax.pie(pcts, colors=colours, startangle=90,
                        wedgeprops={"width": 0.5, "linewidth": 2, "edgecolor": "white"})
    for wedge, cat, pct in zip(wedges, categories, pcts):
        angle = (wedge.theta1 + wedge.theta2) / 2
        rad = np.radians(angle)
        x_o, y_o = 1.22 * np.cos(rad), 1.22 * np.sin(rad)
        ax.annotate(f"{cat}\n{pct:.1f}%", xy=(0.88*np.cos(rad), 0.88*np.sin(rad)),
                    xytext=(x_o, y_o), fontsize=7.5,
                    ha="left" if x_o > 0 else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color="#AAAAAA", lw=0.6))
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)


def treemap(population_layers: list, width=65, height=45, tweaks=[], report_context=None):
    """Treemap — area-proportional category rectangles."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    metric = base.metrics[0]
    categories = metric.category_names
    counts = metric.stats.component_counts
    total = sum(c for c in counts if c is not None) or 1
    pcts = [c / total * 100 for c in counts]
    colours = PIE_COLOURS[:len(categories)]
    sorted_items = sorted(zip(pcts, categories, colours), reverse=True)
    x_cursor = 0
    for pct, cat, col in sorted_items:
        bw = pct / 100
        rect = plt.Rectangle((x_cursor, 0), bw, 1.0,
                              facecolor=col, edgecolor="white", linewidth=2)
        ax.add_patch(rect)
        cx, cy = x_cursor + bw / 2, 0.5
        if bw > 0.06:
            ax.text(cx, cy + 0.15, cat, ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold")
            ax.text(cx, cy - 0.15, f"{pct:.1f}%", ha="center", va="center",
                    fontsize=8, color="white")
        x_cursor += bw
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, None)
