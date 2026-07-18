"""
numeric_series.py
Base Chart functions for the NumericSeries data shape: one or more
independent numeric Metric-Series, one value per unit per metric.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

from core.shared.normalisation_containers.shapes import autotable_stats
from core.output_generation.execution.charts.base_charts.shared import (
    BAR_BLUE, MEAN_COL, MEDIAN_COL, QUARTILE_COL, NAVY, ORANGE, HIGHLIGHT, PEER_COLOURS,
    _size_to_inches, _fig_to_bytes, _apply_spine_style, _format_number, _axis_formatter,
    _resolve_unit_colours, _population_legend_handles, _get_selected_unit,
    _selected_layer_value, _autotable_with_selection,
)


def ranked_column(population_layers: list, width=80, height=50, tweaks=[], report_context=None):
    """Ranked descending column chart with mean/median/quartile reference lines."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    ms = base.metric_stats[0]
    units = sorted(base.units, key=lambda u: (u.values[0] is None, -(u.values[0] or 0)))
    codes  = [u.unit_code for u in units]
    values = [u.values[0] if u.values[0] is not None else 0 for u in units]
    x = np.arange(len(codes))

    colours = _resolve_unit_colours(units, population_layers)
    ax.bar(x, values, color=colours, width=0.8, zorder=2)

    sel_idx, sel_val, _ = _get_selected_unit(units, report_context)
    if sel_idx is not None and sel_val is not None:
        ax.annotate(report_context.unit_code,
                    xy=(sel_idx, sel_val), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=7, color=HIGHLIGHT, fontweight="bold")

    if ms.mean   is not None: ax.axhline(ms.mean,   color=MEAN_COL,    linewidth=1.5, zorder=3)
    if ms.median is not None: ax.axhline(ms.median, color=MEDIAN_COL,  linewidth=1.5, zorder=3)
    if ms.q1     is not None: ax.axhline(ms.q1,     color=QUARTILE_COL, linewidth=1, linestyle="--", zorder=3)
    if ms.q3     is not None: ax.axhline(ms.q3,     color=QUARTILE_COL, linewidth=1, linestyle="--", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(codes, rotation=90, fontsize=7)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)

    label = base.metric_names[0] if base.metric_names else "Value"
    handles = _population_legend_handles(population_layers, label)
    handles += [
        plt.Line2D([0],[0], color=MEAN_COL,     linewidth=1.5, label="Mean"),
        plt.Line2D([0],[0], color=MEDIAN_COL,   linewidth=1.5, label="Median"),
        plt.Line2D([0],[0], color=QUARTILE_COL, linewidth=1, linestyle="--", label="Lower/Upper Quartiles"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.28),
              ncol=4, fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, sel_val)


def dot_strip(population_layers: list, width=80, height=40, tweaks=[], report_context=None):
    """Strip / dot plot — one dot per unit ranked left to right."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    ms = base.metric_stats[0]
    units = sorted(base.units, key=lambda u: (u.values[0] is None, u.values[0] or 0))
    values = [u.values[0] for u in units if u.values[0] is not None]
    x = np.arange(len(values))

    colours = _resolve_unit_colours(units, population_layers)
    sizes   = [80 if c == HIGHLIGHT else 30 for c in colours]
    ax.scatter(x, values, color=colours, s=sizes, zorder=3, alpha=0.9)

    sel_idx, sel_val, _ = _get_selected_unit(units, report_context)
    if sel_idx is not None and sel_val is not None:
        ax.annotate(report_context.unit_code,
                    xy=(sel_idx, sel_val), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=7, color=HIGHLIGHT, fontweight="bold")

    if ms.mean   is not None: ax.axhline(ms.mean,   color=MEAN_COL,    linewidth=1.5, zorder=2)
    if ms.median is not None: ax.axhline(ms.median, color=MEDIAN_COL,  linewidth=1.5, zorder=2)
    if ms.q1     is not None: ax.axhline(ms.q1,     color=QUARTILE_COL, linewidth=1, linestyle="--", zorder=2)
    if ms.q3     is not None: ax.axhline(ms.q3,     color=QUARTILE_COL, linewidth=1, linestyle="--", zorder=2)
    ax.set_xticks([])
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.set_xlabel(f"n = {len(values)} organisations", fontsize=8, color="#555555")

    label = base.metric_names[0] if base.metric_names else "Value"
    handles = _population_legend_handles(population_layers, label)
    handles += [
        plt.Line2D([0],[0], color=MEAN_COL,     linewidth=1.5, label="Mean"),
        plt.Line2D([0],[0], color=MEDIAN_COL,   linewidth=1.5, label="Median"),
        plt.Line2D([0],[0], color=QUARTILE_COL, linewidth=1, linestyle="--", label="Quartiles"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=4, fontsize=7, frameon=False)
    fig.tight_layout()
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, sel_val)


def box_whisker(population_layers: list, width=50, height=50, tweaks=[], report_context=None):
    """Box and whisker — distribution from first shape, markers for subsequent layers."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    values = [u.values[0] for u in base.units if u.values[0] is not None]
    ax.boxplot(values, vert=True, patch_artist=True, widths=0.5,
               medianprops=dict(color=MEDIAN_COL, linewidth=2),
               boxprops=dict(facecolor=BAR_BLUE, color=NAVY, linewidth=1.2),
               whiskerprops=dict(color=NAVY, linewidth=1.2),
               capprops=dict(color=NAVY, linewidth=1.2),
               flierprops=dict(marker="o", color=ORANGE, markersize=4, alpha=0.7, markeredgewidth=0))
    ms = base.metric_stats[0]
    if ms.mean is not None:
        ax.axhline(ms.mean, color=MEAN_COL, linewidth=1.5, linestyle="--")

    extra_handles = []
    peer_colour_idx = 0
    for layer in population_layers[1:]:
        if layer.population_label == "Selected":
            sel_units = layer.units
            if sel_units and sel_units[0].values[0] is not None:
                sv = sel_units[0].values[0]
                ax.scatter([1], [sv], color=HIGHLIGHT, zorder=7, s=80, marker="D")
                ax.axhline(sv, color=HIGHLIGHT, linewidth=1, linestyle=":", zorder=5, alpha=0.6)
                extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                    markerfacecolor=HIGHLIGHT, markersize=7,
                    label=f"{report_context.unit_code}: {_format_number(sv, base.format_modifier)}" if report_context else "Selected"))
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            peer_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
            if peer_vals and report_context:
                sel_in_peer = next((u.values[0] for u in layer.units
                                    if u.unit_id == report_context.unit_id
                                    and u.values[0] is not None), None)
                if sel_in_peer is not None:
                    ax.scatter([1], [sel_in_peer], color=colour, zorder=6, s=60, marker="D", alpha=0.85)
                    ax.axhline(sel_in_peer, color=colour, linewidth=0.8, linestyle=":", zorder=5, alpha=0.5)
                    extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                        markerfacecolor=colour, markersize=6, label=layer.population_label))

    ax.set_xticks([])
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=9)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.set_xlabel(f"n = {len(values)}", fontsize=8, color="#555555")
    handles = [
        mpatches.Patch(facecolor=BAR_BLUE, edgecolor=NAVY, label="IQR"),
        plt.Line2D([0],[0], color=MEDIAN_COL, linewidth=2,
                   label=f"Median: {_format_number(ms.median, base.format_modifier)}" if ms.median is not None else "Median"),
        plt.Line2D([0],[0], color=MEAN_COL, linewidth=1.5, linestyle="--",
                   label=f"Mean: {_format_number(ms.mean, base.format_modifier)}" if ms.mean is not None else "Mean"),
        plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=ORANGE, markersize=5, label="Outliers"),
    ] + extra_handles
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    sel_val = _selected_layer_value(population_layers)
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, sel_val)


def frequency_histogram(population_layers: list, width=60, height=45, tweaks=[], report_context=None):
    """Frequency histogram — distribution from first shape, reference lines for subsequent layers."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    values = [u.values[0] for u in base.units if u.values[0] is not None]
    n_bins = min(max(int(np.sqrt(len(values))), 8), 20)
    ax.hist(values, bins=n_bins, color=BAR_BLUE, edgecolor="white", linewidth=0.8, zorder=2)
    ms = base.metric_stats[0]
    if ms.mean   is not None: ax.axvline(ms.mean,   color=MEAN_COL,   linewidth=1.5, label=f"Mean: {_format_number(ms.mean, base.format_modifier)}")
    if ms.median is not None: ax.axvline(ms.median, color=MEDIAN_COL, linewidth=1.5, label=f"Median: {_format_number(ms.median, base.format_modifier)}")

    peer_colour_idx = 0
    for layer in population_layers[1:]:
        if layer.population_label == "Selected":
            sel_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
            if sel_vals and report_context:
                sv = sel_vals[0]
                ax.axvline(sv, color=HIGHLIGHT, linewidth=2, linestyle="--", zorder=4,
                           label=f"{report_context.unit_code}: {_format_number(sv, base.format_modifier)}")
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            peer_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
            if peer_vals:
                peer_mean = float(np.mean(peer_vals))
                ax.axvline(peer_mean, color=colour, linewidth=1.5, linestyle="--",
                           label=f"{layer.population_label} mean: {_format_number(peer_mean, base.format_modifier)}")

    ax.xaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(labelsize=8)
    ax.set_ylabel("Count", fontsize=8)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    sel_val = _selected_layer_value(population_layers)
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, sel_val)


def violin_plot(population_layers: list, width=50, height=50, tweaks=[], report_context=None):
    """Violin plot — distribution from first shape, markers for subsequent layers."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    fig, ax = plt.subplots(figsize=(w, h))
    values = [u.values[0] for u in base.units if u.values[0] is not None]
    parts = ax.violinplot(values, vert=True, showmedians=True, showextrema=True)
    for pc in parts["bodies"]:
        pc.set_facecolor(BAR_BLUE); pc.set_edgecolor(NAVY); pc.set_alpha(0.75)
    parts["cmedians"].set_color(MEDIAN_COL); parts["cmedians"].set_linewidth(2)
    parts["cmaxes"].set_color(NAVY); parts["cmins"].set_color(NAVY); parts["cbars"].set_color(NAVY)
    ms = base.metric_stats[0]
    if ms.mean is not None:
        ax.scatter([1], [ms.mean], color=MEAN_COL, zorder=5, s=50)

    extra_handles = []
    peer_colour_idx = 0
    for layer in population_layers[1:]:
        if layer.population_label == "Selected":
            sel_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
            if sel_vals and report_context:
                sv = sel_vals[0]
                ax.scatter([1], [sv], color=HIGHLIGHT, zorder=7, s=80, marker="D")
                ax.axhline(sv, color=HIGHLIGHT, linewidth=1, linestyle=":", zorder=5, alpha=0.6)
                extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                    markerfacecolor=HIGHLIGHT, markersize=7,
                    label=f"{report_context.unit_code}: {_format_number(sv, base.format_modifier)}"))
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            peer_colour_idx += 1
            if report_context:
                sel_in_peer = next((u.values[0] for u in layer.units
                                    if u.unit_id == report_context.unit_id
                                    and u.values[0] is not None), None)
                if sel_in_peer is not None:
                    ax.scatter([1], [sel_in_peer], color=colour, zorder=6, s=60, marker="D", alpha=0.85)
                    ax.axhline(sel_in_peer, color=colour, linewidth=0.8, linestyle=":", zorder=5, alpha=0.5)
                    extra_handles.append(plt.Line2D([0],[0], marker="D", color="w",
                        markerfacecolor=colour, markersize=6, label=layer.population_label))

    ax.set_xticks([])
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=9)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7)
    _apply_spine_style(ax)
    ax.set_xlabel(f"n = {len(values)}", fontsize=8, color="#555555")
    handles = [
        mpatches.Patch(facecolor=BAR_BLUE, edgecolor=NAVY, alpha=0.75, label="Distribution"),
        plt.Line2D([0],[0], color=MEDIAN_COL, linewidth=2,
                   label=f"Median: {_format_number(ms.median, base.format_modifier)}" if ms.median is not None else "Median"),
        plt.Line2D([0],[0], marker="o", color="w", markerfacecolor=MEAN_COL, markersize=6,
                   label=f"Mean: {_format_number(ms.mean, base.format_modifier)}" if ms.mean is not None else "Mean"),
    ] + extra_handles
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()
    sel_val = _selected_layer_value(population_layers)
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, sel_val)


def bead_string_dot_plot(population_layers: list, width=80, height=40, tweaks=[], report_context=None):
    """Multi-tier bead-string dot plot — one tier per population layer."""
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    base = population_layers[0]
    ms   = base.metric_stats[0] if base.metric_stats else None
    vals = [u.values[0] for u in base.units if u.values[0] is not None]
    if not vals:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    COLOUR_ALL = (136/255, 135/255, 128/255, 0.38)
    STRING_ALL = (136/255, 135/255, 128/255, 0.25)
    COLOUR_SEL = "#185FA5"
    STRING_SEL = (24/255, 95/255, 165/255, 0.20)

    tiers = []
    peer_colour_idx = 0
    for layer in population_layers:
        tier_ids  = [u.unit_id for u in layer.units if u.values[0] is not None]
        tier_vals = [u.values[0] for u in layer.units if u.values[0] is not None]
        if not tier_vals:
            continue
        if layer.population_label == "All":
            tiers.append({"ids": tier_ids, "vals": tier_vals, "dot": COLOUR_ALL, "string": STRING_ALL,
                          "label": "All organisations", "opaque": False})
        elif layer.population_label == "Selected":
            tiers.append({"ids": tier_ids, "vals": tier_vals, "dot": COLOUR_SEL, "string": STRING_SEL,
                          "label": layer.population_label or "Selected", "opaque": True})
        else:
            raw = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            r, g, b = mcolors.to_rgb(raw)
            tiers.append({"ids": tier_ids, "vals": tier_vals, "dot": (r, g, b, 0.42), "string": (r, g, b, 0.20),
                          "label": layer.population_label, "opaque": False})
            peer_colour_idx += 1

    if not tiers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig), {}

    # Visual-only de-duplication: a unit already shown in a more specific
    # (later-token) tier is suppressed from every broader (earlier-token)
    # tier's dots, so e.g. the Selected unit(s) only appear once, in
    # Selected, rather than also as a dot in Region() and All. Stats (ms,
    # autotable) are computed from `base` and from the Selected tier's own
    # values below, both untouched by this — it only affects which dots get
    # drawn.
    already_shown = set()
    for t in reversed(tiers):
        original_ids = list(t["ids"])
        if already_shown:
            keep = [(uid, v) for uid, v in zip(t["ids"], t["vals"]) if uid not in already_shown]
            t["ids"]  = [uid for uid, v in keep]
            t["vals"] = [v for uid, v in keep]
        already_shown.update(original_ids)

    n_tiers = len(tiers)
    w, _   = _size_to_inches(width, height)
    TIER_GAP = 0.40; LABEL_COL = 1.6; DOT_SIZE = 38
    INCHES_PER_TIER = 0.28; MARGIN_TOP = 0.40; MARGIN_BOT = 0.25
    h = n_tiers * INCHES_PER_TIER + MARGIN_TOP + MARGIN_BOT

    for i, t in enumerate(tiers):
        t["y"] = i * TIER_GAP

    y_min = -TIER_GAP
    y_max = (n_tiers - 1) * TIER_GAP + TIER_GAP

    all_vals_flat = [v for t in tiers for v in t["vals"]]
    x_min = min(all_vals_flat); x_max = max(all_vals_flat)
    pad = (x_max - x_min) * 0.05 or 1.0
    x_min -= pad; x_max += pad

    if ms:
        q1, q3, median = ms.q1, ms.q3, ms.median
    else:
        q1 = float(np.percentile(vals, 25))
        q3 = float(np.percentile(vals, 75))
        median = float(np.median(vals))

    fig = plt.figure(figsize=(w, h))
    left_frac   = LABEL_COL / w
    bottom_frac = MARGIN_BOT / h
    height_frac = (h - MARGIN_TOP - MARGIN_BOT) / h
    ax = fig.add_axes([left_frac, bottom_frac, 1 - left_frac - 0.02, height_frac])

    ax.set_xlim(x_min, x_max); ax.set_ylim(y_min, y_max); ax.set_yticks([])
    ax.spines["left"].set_visible(False); ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False); ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", labelsize=7.5, color="#AAAAAA"); ax.xaxis.grid(False)

    if q1 is not None and q3 is not None:
        iqr_rect = mpatches.FancyBboxPatch(
            (q1, y_min), q3 - q1, y_max - y_min,
            boxstyle="square,pad=0",
            facecolor=(181/255, 212/255, 244/255, 0.38), edgecolor="none", zorder=1)
        ax.add_patch(iqr_rect)
        label_y = y_max + TIER_GAP * 0.08
        ax.text(q1, label_y, f"Q1\n{_format_number(q1, base.format_modifier)}", ha="center", va="bottom",
                fontsize=6.5, color=(100/255, 130/255, 180/255, 0.85))
        ax.text(q3, label_y, f"Q3\n{_format_number(q3, base.format_modifier)}", ha="center", va="bottom",
                fontsize=6.5, color=(100/255, 130/255, 180/255, 0.85))

    if median is not None:
        ax.vlines(median, y_min, y_max, colors="#E24B4A", linewidth=1.2, linestyles="dashed", zorder=3)
        ax.text(median, y_max + TIER_GAP * 0.08, f"Median\n{_format_number(median, base.format_modifier)}",
                ha="center", va="bottom", fontsize=6.5, color="#E24B4A")

    for t in tiers:
        y = t["y"]; dot = t["dot"]; str_c = t["string"]
        ax.hlines(y, x_min, x_max, colors=[str_c], linewidths=0.5, zorder=2)
        alpha = 1.0 if t["opaque"] else (dot[3] if len(dot) == 4 else 1.0)
        dot_c = dot[:3] if isinstance(dot, tuple) else dot
        ax.scatter(t["vals"], [y] * len(t["vals"]),
                   s=DOT_SIZE, c=[dot_c] * len(t["vals"]),
                   alpha=alpha, linewidths=0, zorder=4)

    if tiers[-1]["opaque"] and tiers[-1]["vals"]:
        sv = tiers[-1]["vals"][0]
        ax.annotate(_format_number(sv, base.format_modifier), xy=(sv, tiers[-1]["y"]),
                    xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=7.5, color=COLOUR_SEL, fontweight="bold")

    ax_pos = ax.get_position()
    for t in tiers:
        y_ax  = (t["y"] - y_min) / (y_max - y_min)
        y_fig = ax_pos.y0 + y_ax * ax_pos.height
        dot_c = t["dot"][:3] if isinstance(t["dot"], tuple) else t["dot"]
        fig.text(ax_pos.x0 - 0.045, y_fig, t["label"],
                 ha="right", va="center", fontsize=7.5, color="#444444")
        r_y = 0.014; r_x = r_y * (h / w)
        fig.patches.append(mpatches.Ellipse(
            (ax_pos.x0 - 0.030, y_fig), width=2*r_x, height=2*r_y,
            transform=fig.transFigure, facecolor=dot_c, edgecolor="none", alpha=0.75, zorder=5))

    sel_val = tiers[-1]["vals"][0] if tiers[-1]["opaque"] and tiers[-1]["vals"] else None
    return _fig_to_bytes(fig), _autotable_with_selection(autotable_stats(base), report_context, sel_val)
