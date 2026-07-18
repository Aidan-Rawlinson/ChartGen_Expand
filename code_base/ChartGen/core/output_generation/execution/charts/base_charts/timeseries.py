"""
timeseries.py
Base Chart functions for the TimeSeries data shape: one or more independent
numeric Metric-Series, one value per unit per metric per period, across a
shared period axis. Renders the first Metric-Series (metrics[0]), the same
"first metric only" convention every other multi-metric shape follows.

A TimeSeries value is a vector indexed by period, not a scalar, so this
module reads metric.units[...].values / period_stats directly rather than
reusing the NumericSeries-shaped single-scalar helpers in shared.py
(_get_selected_unit, _resolve_unit_colours, _selected_layer_value) — the
same reason NumericCompositional/CategoricalCompositional charts don't use
those helpers either.

Population layers arrive as a list of filtered TimeSeries copies with the
same population_label convention as every other shape. Follows the
box_whisker/violin_plot convention: population_layers[0] is always the
scope and drives the main rendering (population mean line, IQR band),
regardless of its own label; population_layers[1:] are highlighted on top
— 'Selected' as the individual unit's own trend line, any other label (a
resolved peer group) as that group's mean line, in PEER_COLOURS order.

Three chart types share this module:
- period_line_chart — population mean + IQR band, Selected/peer lines on top.
- median_comparison_linechart — median per layer instead of mean; Selected
  charts the actual unit value(s) rather than a median, since a median of
  one unit's own value(s) isn't a meaningful statistic in the way it is for
  a wider population.
- full_lines_linechart — every individual unit in population_layers[0] (the
  scope, and by construction the largest population any layer resolves
  against) drawn as a light grey line; every subsequent layer's own unit
  line(s) drawn on top, highlighted the same way as the other two charts.
"""

import numpy as np
import matplotlib.pyplot as plt

from core.shared.normalisation_containers.shapes import autotable_stats
from core.output_generation.execution.charts.base_charts.shared import (
    BAR_BLUE, MEAN_COL, HIGHLIGHT, PEER_COLOURS, NAVY, GREY_LIGHT,
    _size_to_inches, _fig_to_bytes, _apply_spine_style, _axis_formatter,
    _autotable_with_selection,
)


def period_line_chart(population_layers: list, width=80, height=45, tweaks=[], report_context=None):
    """Line chart of one Metric-Series across every period — population mean/IQR band, plus a highlighted line per subsequent layer (Selected or peer group)."""
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    x = np.arange(len(base.periods))
    labels = [p.period_label for p in base.periods]

    means = [ps.mean for ps in metric.period_stats]
    ax.plot(x, means, color=MEAN_COL, linewidth=2, zorder=2, label="Population mean")
    q1 = [ps.q1 for ps in metric.period_stats]
    q3 = [ps.q3 for ps in metric.period_stats]
    if q1 and q3 and all(v is not None for v in q1) and all(v is not None for v in q3):
        ax.fill_between(x, q1, q3, color=BAR_BLUE, alpha=0.25, zorder=1, label="IQR")

    selected_value = None
    peer_colour_idx = 0
    for layer in population_layers[1:]:
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        if layer.population_label == "Selected":
            unit = layer_metric.units[0] if layer_metric.units else None
            if unit is not None:
                ax.plot(x, unit.values, color=HIGHLIGHT, linewidth=2, marker="o",
                        markersize=4, zorder=4,
                        label=report_context.unit_code if report_context else "Selected")
                selected_value = next((v for v in reversed(unit.values) if v is not None), None)
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            peer_means = [ps.mean for ps in layer_metric.period_stats]
            ax.plot(x, peer_means, color=colour, linewidth=1.5, linestyle="--", zorder=3,
                    label=layer.population_label)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()

    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, selected_value)


def median_comparison_linechart(population_layers: list, width=80, height=45, tweaks=[], report_context=None):
    """Line chart of one Metric-Series across every period — median line per population layer, except 'Selected', which charts the actual unit value(s) instead of a median."""
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    x = np.arange(len(base.periods))
    labels = [p.period_label for p in base.periods]

    selected_value = None
    peer_colour_idx = 0

    for i, layer in enumerate(population_layers):
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue

        if layer.population_label == "Selected":
            for unit in layer_metric.units:
                ax.plot(x, unit.values, color=HIGHLIGHT, linewidth=2, marker="o",
                        markersize=4, zorder=4)
            if layer_metric.units:
                ax.plot([], [], color=HIGHLIGHT, linewidth=2, marker="o", markersize=4,
                        label=report_context.unit_code if report_context else "Selected")
                selected_value = next(
                    (v for v in reversed(layer_metric.units[0].values) if v is not None), None
                )
        elif i == 0:
            medians = [ps.median for ps in layer_metric.period_stats]
            ax.plot(x, medians, color=NAVY, linewidth=2, zorder=2,
                    label=f"{layer.population_label} median")
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            medians = [ps.median for ps in layer_metric.period_stats]
            ax.plot(x, medians, color=colour, linewidth=1.5, linestyle="--", zorder=3,
                    label=f"{layer.population_label} median")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()

    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, selected_value)


def full_lines_linechart(population_layers: list, width=80, height=45, tweaks=[], report_context=None):
    """Line chart of one Metric-Series across every period — every individual unit in the largest population (population_layers[0], the scope) drawn as a light grey line; every subsequent population layer's own unit line(s) drawn on top, highlighted."""
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    x = np.arange(len(base.periods))
    labels = [p.period_label for p in base.periods]

    for unit in metric.units:
        ax.plot(x, unit.values, color=GREY_LIGHT, linewidth=0.6, alpha=0.5, zorder=1)
    if metric.units:
        ax.plot([], [], color=GREY_LIGHT, linewidth=1.5,
                label=base.population_label or "All units")

    selected_value = None
    peer_colour_idx = 0
    for layer in population_layers[1:]:
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        if layer.population_label == "Selected":
            for unit in layer_metric.units:
                ax.plot(x, unit.values, color=HIGHLIGHT, linewidth=2, marker="o",
                        markersize=4, zorder=4)
            if layer_metric.units:
                ax.plot([], [], color=HIGHLIGHT, linewidth=2, marker="o", markersize=4,
                        label=report_context.unit_code if report_context else "Selected")
                selected_value = next(
                    (v for v in reversed(layer_metric.units[0].values) if v is not None), None
                )
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            for unit in layer_metric.units:
                ax.plot(x, unit.values, color=colour, linewidth=1.3, zorder=3)
            ax.plot([], [], color=colour, linewidth=1.3, label=layer.population_label)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()

    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, selected_value)
