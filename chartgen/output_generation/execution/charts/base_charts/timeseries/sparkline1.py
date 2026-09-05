"""Base Chart, TimeSeries, sparkline variant. Two lines only, the scope's median per period and the Selected unit's own value per period. No axes, ticks, gridlines, legend or title, so it renders cleanly at very small sizes. Peer-group layers are ignored."""

import io
import warnings
warnings.filterwarnings("ignore")

import colorsys
import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.transforms as mtransforms

MEDIAN_COL      = "#7CB9E8"
SUBMISSION_COL  = "#C12958"

EMU_PER_INCH = 914400
MM_IN_INCHES = 1 / 25.4

TEXT_SCALE = 5

INNER_GAP_IN = (0.015 + 2 * MM_IN_INCHES) * 2 / 3 * TEXT_SCALE
OUTER_GAP_IN = (2 * MM_IN_INCHES) / 3 * TEXT_SCALE


def _shade(hex_colour, lightness_delta, saturation_delta=0.0):
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1.0, max(0.0, l + lightness_delta))
    s = min(1.0, max(0.0, s + saturation_delta))
    return colorsys.hls_to_rgb(h, l, s)


MEDIAN_LINE_COL = _shade(MEDIAN_COL, -0.22, 0.10)


def _format_number(value, format_modifier):
    if value is None:
        return ""
    if format_modifier == "P":
        return f"{value:,.0f}%"
    if format_modifier == "C":
        return f"£{value:,.0f}"
    return f"{value:,.0f}"


def _finite_or_none(v):
    if v is None:
        return None
    return None if v != v else v


def _add_end_labels(fig, ax, side, median_val, submission_val,
                     submission_code, format_modifier):
    entries = []
    if median_val is not None:
        entries.append((f"Median: {_format_number(median_val, format_modifier)}",
                         MEDIAN_LINE_COL, median_val))
    if submission_val is not None:
        prefix = f"{submission_code}: " if submission_code else ""
        entries.append((f"{prefix}{_format_number(submission_val, format_modifier)}",
                         SUBMISSION_COL, submission_val))
    if not entries:
        return
    if len(entries) == 2:
        entries.sort(key=lambda e: e[2], reverse=True)
        y_positions = [0.70, 0.30]
    else:
        y_positions = [0.5]

    if side == "left":
        x_anchor, ha, offset_x_in = 0.0, "right", -INNER_GAP_IN
    else:
        x_anchor, ha, offset_x_in = 1.0, "left", INNER_GAP_IN
    transform = mtransforms.offset_copy(ax.transAxes, fig=fig,
                                         x=offset_x_in, y=0, units="inches")

    for (text, colour, _), y in zip(entries, y_positions):
        ax.text(x_anchor, y, text, transform=transform, color=colour,
                fontsize=7 * TEXT_SCALE, fontweight="bold", ha=ha, va="center",
                clip_on=False)


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _draw_internal_gap_bridges(ax, x, values_raw, color):
    n = len(values_raw)
    i = 0
    while i < n:
        if values_raw[i] is not None:
            i += 1
            continue
        start = i
        while i < n and values_raw[i] is None:
            i += 1
        end = i
        if start > 0 and end < n and values_raw[start - 1] is not None and values_raw[end] is not None:
            ax.plot(
                [x[start - 1], x[end]], [values_raw[start - 1], values_raw[end]],
                color=color, linewidth=0.8 * TEXT_SCALE, linestyle=(0, (1 * TEXT_SCALE, 2.4 * TEXT_SCALE)),
                dash_capstyle="round", zorder=1.5,
            )


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg",
                facecolor="none", edgecolor="none", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _inset_axes_to_fit(fig, ax, box_left_in, box_bottom_in, box_width_in, box_height_in):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    tight = fig.get_tightbbox(renderer)

    box_right_in = box_left_in + box_width_in
    box_top_in = box_bottom_in + box_height_in
    left_margin_in = max(0.0, box_left_in - tight.x0) + OUTER_GAP_IN
    right_margin_in = max(0.0, tight.x1 - box_right_in) + OUTER_GAP_IN
    bottom_margin_in = max(0.0, box_bottom_in - tight.y0)
    top_margin_in = max(0.0, tight.y1 - box_top_in)

    fig_w_in = fig.get_figwidth()
    fig_h_in = fig.get_figheight()
    new_left = (box_left_in + left_margin_in) / fig_w_in
    new_width = (box_width_in - left_margin_in - right_margin_in) / fig_w_in
    new_bottom = (box_bottom_in + bottom_margin_in) / fig_h_in
    new_height = (box_height_in - bottom_margin_in - top_margin_in) / fig_h_in
    ax.set_position([new_left, new_bottom, max(new_width, 0.01), max(new_height, 0.01)])

    box_bbox = mtransforms.Bbox.from_bounds(
        box_left_in, box_bottom_in, box_width_in, box_height_in
    ).transformed(fig.dpi_scale_trans)
    for artist in ax.get_children():
        if hasattr(artist, "get_clip_on") and not artist.get_clip_on():
            artist.set_clip_box(box_bbox)
            artist.set_clip_on(True)


def _blank_chart(width_emu, height_emu):
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    ax.axis("off")
    return _fig_to_bytes(fig)


def sparkline1(population_layers: list, width_emu=2736215, height_emu=684054, tweaks=""):
    if not population_layers:
        return _blank_chart(width_emu, height_emu)

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        return _blank_chart(width_emu, height_emu)

    v_border_emu = 0.05 * height_emu
    h_border_emu = v_border_emu / 6
    h_border_emu = min(h_border_emu, max(width_emu / 2 - 1, 0))

    w, h = _size_to_inches(width_emu, height_emu)
    h_border_in = h_border_emu / EMU_PER_INCH
    v_border_in = v_border_emu / EMU_PER_INCH
    inner_left_in = h_border_in
    inner_bottom_in = v_border_in
    inner_width_in = w - 2 * h_border_in
    inner_height_in = h - 2 * v_border_in

    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_position([
        inner_left_in / w, inner_bottom_in / h,
        inner_width_in / w, inner_height_in / h,
    ])
    x = np.arange(len(base.periods))

    medians = [ps.median for ps in metric.period_stats]
    has_medians = bool(medians) and all(v is not None for v in medians)

    submission_unit = None
    for layer in population_layers[1:]:
        if layer.population_label != "Selected":
            continue
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        unit = layer_metric.units[0] if layer_metric.units else None
        if unit is not None and unit.values:
            submission_unit = unit

    submission_values_raw = submission_unit.values if submission_unit else None
    has_submission = bool(submission_values_raw) and any(v is not None for v in submission_values_raw)
    submission_values = None
    submission_values_present = []
    if has_submission:
        submission_values = [float(v) if v is not None else float("nan") for v in submission_values_raw]
        submission_values_present = [v for v in submission_values_raw if v is not None]

    all_values = []
    if has_medians:
        all_values.extend(medians)
    if submission_values_present:
        all_values.extend(submission_values_present)

    axis_bottom, axis_top = None, None
    if all_values:
        data_min, data_max = min(all_values), max(all_values)
        data_range = data_max - data_min
        buffer = data_range * 0.125 if data_range > 0 else max(abs(data_max), 1) * 0.1
        axis_bottom, axis_top = data_min - buffer, data_max + buffer

    if has_medians:
        baseline = axis_bottom if axis_bottom is not None else min(medians)
        top_colour = _shade(MEDIAN_COL, -0.01, 0.04)
        bottom_colour = (1.0, 1.0, 1.0)
        fade = mcolors.LinearSegmentedColormap.from_list(
            "median_fade", [bottom_colour, top_colour])
        gradient = np.linspace(0, 1, 256).reshape(-1, 1)
        poly = ax.fill_between(x, medians, baseline, color="none", zorder=0)
        im = ax.imshow(gradient, extent=[x[0], x[-1], baseline, max(medians)],
                        origin="lower", aspect="auto", cmap=fade, alpha=0.48,
                        zorder=0)
        im.set_clip_path(poly.get_paths()[0], transform=ax.transData)
        ax.plot(x, medians, color=MEDIAN_LINE_COL, linewidth=1.0 * TEXT_SCALE, zorder=1,
                solid_capstyle="round")

    if submission_values:
        _draw_internal_gap_bridges(ax, x, submission_values_raw, SUBMISSION_COL)
        ax.plot(x, submission_values, color=SUBMISSION_COL, linewidth=0.8 * TEXT_SCALE,
                zorder=2, solid_capstyle="round")
        ax.plot(x, submission_values, linestyle="none", marker="o",
                markersize=1.333 * TEXT_SCALE, color=SUBMISSION_COL, zorder=3)

    if has_medians:
        ax.plot([x[0], x[-1]], [medians[0], medians[-1]], linestyle="none",
                marker="o", markersize=2.667 * TEXT_SCALE, color=MEDIAN_LINE_COL, zorder=2,
                clip_on=False)
    if submission_values:
        ax.plot([x[0], x[-1]], [submission_values[0], submission_values[-1]],
                linestyle="none", marker="o", markersize=2.667 * TEXT_SCALE,
                color=SUBMISSION_COL, zorder=4, clip_on=False)

    ax.axis("off")
    ax.margins(x=0.02)
    if axis_bottom is not None:
        ax.set_ylim(axis_bottom, axis_top)

    format_modifier = getattr(base, "format_modifier", None)
    submission_code = submission_unit.unit_code if submission_unit else None
    _add_end_labels(
        fig, ax, "left",
        medians[0] if has_medians else None,
        _finite_or_none(submission_values[0]) if submission_values else None,
        submission_code, format_modifier,
    )
    _add_end_labels(
        fig, ax, "right",
        medians[-1] if has_medians else None,
        _finite_or_none(submission_values[-1]) if submission_values else None,
        submission_code, format_modifier,
    )

    _inset_axes_to_fit(fig, ax, inner_left_in, inner_bottom_in, inner_width_in, inner_height_in)

    return _fig_to_bytes(fig)
