"""
bead_string_dot_plot.py
Base Chart — NumericSeries. Multi-tier bead-string dot plot, one tier per
population layer.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) — no report_context or any other runtime object. This
chart never needed one: it reads unit identity and the "Selected" label
directly from population_layers, the same as the other charts.
"""

import warnings
warnings.filterwarnings("ignore")

import io
import numpy as np
import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font, baked into the SVG
# vector output as real glyph outlines (svg.fonttype default "path").
# See Architecture, SVG rendering methodology.
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

# ---------------------------------------------------------------------------
# Palette / sizing / formatting — inlined, this chart's own copy
# ---------------------------------------------------------------------------

PEER_COLOURS = ["#2E9E75", "#7030A0", "#E87722", "#2E86AB"]

EMU_PER_INCH = 914400


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


def bead_string_dot_plot(population_layers: list, width_emu=5486400, height_emu=2743200, tweaks=""):
    """Multi-tier bead-string dot plot — one tier per population layer."""
    if not population_layers:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig)

    base = population_layers[0]
    ms   = base.metric_stats[0] if base.metric_stats else None
    vals = [u.values[0] for u in base.units if u.values[0] is not None]
    if not vals:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_bytes(fig)

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
        return _fig_to_bytes(fig)

    # Visual-only de-duplication: a unit already shown in a more specific
    # (later-token) tier is suppressed from every broader (earlier-token)
    # tier's dots, so e.g. the Selected unit(s) only appear once, in
    # Selected, rather than also as a dot in Region() and All. Stats (ms)
    # are computed from `base` above, untouched by this — it only affects
    # which dots get drawn.
    already_shown = set()
    for t in reversed(tiers):
        original_ids = list(t["ids"])
        if already_shown:
            keep = [(uid, v) for uid, v in zip(t["ids"], t["vals"]) if uid not in already_shown]
            t["ids"]  = [uid for uid, v in keep]
            t["vals"] = [v for uid, v in keep]
        already_shown.update(original_ids)

    n_tiers = len(tiers)
    w, _   = _size_to_inches(width_emu, height_emu)
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

    return _fig_to_bytes(fig)
