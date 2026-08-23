"""Base Chart, TimeSeries. Mean and median reference lines across every period, a highlighted line per subsequent population layer, and a per-period table of Selected, Mean and Median values beneath the chart. Chart, legend and table each occupy a fixed non-overlapping band. CI report styling."""

import io
import math
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches

SELECTED_COL   = "#DA291C"
MEAN_COL       = "#009639"
MEDIAN_COL     = "#78BE20"
OTHER_COL      = "#005EB8"
GRID_COL       = "#DFE6EE"
BASELINE_COL   = "#2F3A45"
AXIS_LABEL_COL = "#5B6770"
CARD_BG        = "#F0F5FC"
LEGEND_BORDER  = "#E6E9ED"
TARGET_PURPLE  = "#9B30FF"

GREYED_HATCH_COL   = "#E9EDF0"
GREYED_DIVIDER_COL = "#E9EDF0"

PEER_ALPHAS = [1.0, 0.7, 0.5, 0.35]

EMU_PER_INCH = 914400

TEXT_SCALE = 5

MARGIN          = 0.055
LABEL_GUTTER    = 0.048
TABLE_HEIGHT    = 0.30
BUFFER_1        = 0.025
LEGEND_HEIGHT   = 0.085
BUFFER_2        = 0.020

_content_left   = MARGIN + LABEL_GUTTER
_content_width  = 1.0 - (2 * MARGIN) - LABEL_GUTTER
_content_bottom = MARGIN
_content_top    = 1.0 - MARGIN

_MONTH_ABBR_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_NUM_TO_NAME = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}


def _hex_to_rgb(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    return tuple(int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def _tint(hex_colour, strength):
    r, g, b = _hex_to_rgb(hex_colour)
    r = 255 - (255 - r) * strength
    g = 255 - (255 - g) * strength
    b = 255 - (255 - b) * strength
    return _rgb_to_hex((r, g, b))


PLOT_BG          = _tint(CARD_BG, 0.25)
TABLE_CELL_BG    = _tint(CARD_BG, 0.25)
HEADER_BG        = _tint(OTHER_COL, 0.35)
ROWLABEL_BG      = _tint("#EFF5FC", 0.6)


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _to_nan_array(values):
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def _month_label(period_label):
    parts = period_label.split()
    if len(parts) != 2:
        return period_label
    month_name, year = parts
    if not year.isdigit():
        return period_label
    return f"{month_name[:3]} {year[-2:]}"


def _parse_period_label(period_label):
    parts = period_label.split()
    if len(parts) != 2:
        return None
    month_name, year_str = parts
    if not year_str.isdigit():
        return None
    month_num = _MONTH_ABBR_TO_NUM.get(month_name[:3].lower())
    if month_num is None:
        return None
    return int(year_str), month_num


def _months_before(year, month, steps):
    zero_based = (year * 12 + (month - 1)) - steps
    return zero_based // 12, (zero_based % 12) + 1


def _build_padding_labels(first_real_label, n_pad):
    parsed = _parse_period_label(first_real_label)
    if parsed is None:
        return None
    year, month = parsed
    labels = []
    for steps in range(n_pad, 0, -1):
        y, m = _months_before(year, month, steps)
        labels.append(f"{_MONTH_NUM_TO_NAME[m]} {y}")
    return labels


def _apply_padding(arr, n_pad, window_size):
    if arr is None:
        return None
    trimmed = arr[-window_size:] if window_size < len(arr) else arr
    if n_pad:
        return np.concatenate([np.full(n_pad, np.nan), trimmed])
    return trimmed


def _format_value(value, format_modifier, decimals):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    if format_modifier == "P":
        return f"{value:,.{decimals}f}%"
    if format_modifier == "C":
        return f"£{value:,.{decimals}f}"
    return f"{value:,.{decimals}f}"


def _axis_formatter(format_modifier, decimals):
    return mticker.FuncFormatter(lambda v, _: _format_value(v, format_modifier, decimals))


def _nice_number(value, round_to_nearest=False):
    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    fraction = value / (10 ** exponent)
    if round_to_nearest:
        if fraction < 1.5:
            nice_fraction = 1
        elif fraction < 2.5:
            nice_fraction = 2
        elif fraction < 3.5:
            nice_fraction = 3
        elif fraction < 4.5:
            nice_fraction = 4
        elif fraction < 7.5:
            nice_fraction = 5
        else:
            nice_fraction = 10
    else:
        if fraction <= 1:
            nice_fraction = 1
        elif fraction <= 2:
            nice_fraction = 2
        elif fraction <= 3:
            nice_fraction = 3
        elif fraction <= 4:
            nice_fraction = 4
        elif fraction <= 5:
            nice_fraction = 5
        else:
            nice_fraction = 10
    return nice_fraction * (10 ** exponent)


def _nice_axis_bounds(max_plotted_value, target_ticks=5):
    if max_plotted_value <= 0:
        return 1.0, 0.2
    padded = max_plotted_value * 1.10
    raw_step = padded / target_ticks
    step = _nice_number(raw_step, round_to_nearest=True)
    y_max = math.ceil(padded / step) * step
    return y_max, step


def _parse_tweaks(tweaks: str) -> dict:
    """This chart's own tweaks grammar: caret-separated key:value pairs, or a bare flag with no colon. Two are read. target:N or target:median draws a reference line. 12m forces a fixed 12-month axis, most recent months rightmost, missing early months padded as an empty hatched band."""
    result = {}
    if not tweaks:
        return result
    for part in tweaks.split("^"):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            result[part.lower()] = True
            continue
        key, _, value = part.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key:
            result[key] = value
    return result


def _sig_fig_decimals(reference_value, sig_figs=3):
    if reference_value is None:
        return 0
    reference_value = abs(reference_value)
    if reference_value == 0 or math.isnan(reference_value):
        return 0
    return max(0, (sig_figs - 1) - math.floor(math.log10(reference_value)))


def _apply_axes_style(ax, y_max, step):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(step))
    ax.yaxis.grid(True, color=GRID_COL, linewidth=0.5 * TEXT_SCALE, zorder=0)
    ax.xaxis.grid(False)
    ax.axhline(0, color=BASELINE_COL, linewidth=0.8 * TEXT_SCALE, zorder=1)
    ax.tick_params(axis="y", labelsize=7 * TEXT_SCALE, colors=AXIS_LABEL_COL, length=0)
    ax.tick_params(axis="x", length=0)


def _empty_chart(width_emu, height_emu):
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)
    ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12 * TEXT_SCALE)
    ax.axis("off")
    return _fig_to_bytes(fig)


def _style_table(table, has_selected_row, n_pad, ax_table):
    table.auto_set_font_size(False)
    table.set_fontsize(7.5 * TEXT_SCALE)

    renderer = ax_table.figure.canvas.get_renderer()
    border_zorder = table.get_zorder() + 1

    row_colours = []
    if has_selected_row:
        row_colours.append(SELECTED_COL)
    row_colours.append(MEAN_COL)
    row_colours.append(MEDIAN_COL)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(LEGEND_BORDER)
        cell.set_linewidth(0.8 * TEXT_SCALE)
        if row == 0:
            cell.set_facecolor(HEADER_BG)
            cell.set_text_props(color=BASELINE_COL, fontweight="bold", fontsize=7 * TEXT_SCALE)
        elif col == -1:
            cell.set_facecolor(ROWLABEL_BG)
            cell.set_text_props(fontweight="bold", fontsize=7 * TEXT_SCALE,
                                 color=row_colours[row - 1])
        elif n_pad and col < n_pad:
            cell.set_facecolor(TABLE_CELL_BG)
            cell.set_edgecolor(GREYED_HATCH_COL)
            cell.set_hatch("///")
            cell.set_text_props(color=AXIS_LABEL_COL, fontsize=7 * TEXT_SCALE, style="italic")
            bbox_display = cell.get_window_extent(renderer)
            bbox_data = bbox_display.transformed(ax_table.transData.inverted())
            border_overlay = mpatches.Rectangle(
                (bbox_data.x0, bbox_data.y0), bbox_data.width, bbox_data.height,
                facecolor="none", edgecolor=LEGEND_BORDER, linewidth=0.8 * TEXT_SCALE,
                zorder=border_zorder,
            )
            ax_table.add_patch(border_overlay)
        else:
            cell.set_facecolor(TABLE_CELL_BG)
            cell.set_text_props(color=AXIS_LABEL_COL, fontsize=7 * TEXT_SCALE)


def line_ci_full(population_layers: list, width_emu=5486400, height_emu=3086100, tweaks=""):
    if not population_layers:
        return _empty_chart(width_emu, height_emu)

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        return _empty_chart(width_emu, height_emu)

    n_real = len(base.periods)

    medians = _to_nan_array([ps.median for ps in metric.period_stats])
    means = _to_nan_array([ps.mean for ps in metric.period_stats])

    selected_y = None
    selected_code = None
    peer_series = []
    peer_alpha_idx = 0

    for layer in population_layers[1:]:
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        if layer.population_label == "Selected":
            unit = layer_metric.units[0] if layer_metric.units else None
            if unit is not None:
                selected_y = _to_nan_array(unit.values)
                selected_code = unit.unit_code or unit.unit_id
        else:
            peer_means = _to_nan_array([ps.mean for ps in layer_metric.period_stats])
            alpha = PEER_ALPHAS[peer_alpha_idx % len(PEER_ALPHAS)]
            peer_alpha_idx += 1
            peer_series.append((peer_means, layer.population_label, alpha))

    tweak_values = _parse_tweaks(tweaks)
    target_raw = tweak_values.get("target")
    target_series = None
    if target_raw:
        if target_raw.lower() == "median":
            target_series = medians
        else:
            try:
                target_series = np.full(n_real, float(target_raw))
            except ValueError:
                target_series = None

    pad_to_12 = bool(tweak_values.get("12m"))
    window_size = n_real
    n_pad = 0
    padded_labels = []
    windowed_periods = base.periods

    if pad_to_12:
        window_size = min(n_real, 12)
        windowed_periods = base.periods[-window_size:] if window_size < n_real else base.periods
        wanted_pad = 12 - window_size
        if wanted_pad > 0:
            built_labels = _build_padding_labels(windowed_periods[0].period_label, wanted_pad)
            if built_labels is not None:
                n_pad = wanted_pad
                padded_labels = built_labels

    means = _apply_padding(means, n_pad, window_size)
    medians = _apply_padding(medians, n_pad, window_size)
    selected_y = _apply_padding(selected_y, n_pad, window_size)
    peer_series = [(_apply_padding(pm, n_pad, window_size), label, alpha)
                   for pm, label, alpha in peer_series]
    target_series = _apply_padding(target_series, n_pad, window_size)

    n_periods = len(means)
    x = np.arange(n_periods)
    month_labels = [_month_label(l) for l in padded_labels] + \
                   [_month_label(p.period_label) for p in windowed_periods]

    all_values = list(means[~np.isnan(means)]) + list(medians[~np.isnan(medians)])
    if selected_y is not None:
        all_values.extend(list(selected_y[~np.isnan(selected_y)]))
    for pm, _, _ in peer_series:
        all_values.extend(list(pm[~np.isnan(pm)]))
    if target_series is not None:
        all_values.extend(list(target_series[~np.isnan(target_series)]))

    max_plotted = max(all_values) if all_values else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)

    w, h = _size_to_inches(width_emu, height_emu)
    fig = plt.figure(figsize=(w, h))
    fig.patch.set_facecolor(CARD_BG)

    table_bottom = _content_bottom
    legend_bottom = table_bottom + TABLE_HEIGHT + BUFFER_1
    chart_bottom = legend_bottom + LEGEND_HEIGHT + BUFFER_2
    chart_height = _content_top - chart_bottom

    ax = fig.add_axes([_content_left, chart_bottom, _content_width, chart_height])
    ax_table = fig.add_axes([_content_left, table_bottom, _content_width, TABLE_HEIGHT])
    ax.set_facecolor(PLOT_BG)
    ax_table.set_facecolor(CARD_BG)

    if n_pad:
        ax.axvspan(-0.5, n_pad - 0.5, facecolor="none", edgecolor=GREYED_HATCH_COL,
                   hatch="///", linewidth=0, zorder=0.5)
        ax.axvline(n_pad - 0.5, color=GREYED_DIVIDER_COL, linewidth=1 * TEXT_SCALE,
                   linestyle=(0, (4 * TEXT_SCALE, 3 * TEXT_SCALE)), zorder=0.6)

    handles = []
    legend_labels = []

    line, = ax.plot(x, medians, color=MEDIAN_COL, linewidth=1.8 * TEXT_SCALE, zorder=2)
    handles.append(line)
    legend_labels.append("Median")

    line, = ax.plot(x, means, color=MEAN_COL, linewidth=1.8 * TEXT_SCALE, zorder=3)
    handles.append(line)
    legend_labels.append("Mean")

    for peer_means, peer_label, alpha in peer_series:
        line, = ax.plot(x, peer_means, color=OTHER_COL, linewidth=1.5 * TEXT_SCALE,
                         linestyle="--", alpha=alpha, zorder=4)
        handles.append(line)
        legend_labels.append(peer_label)

    if selected_y is not None:
        line, = ax.plot(x, selected_y, color=SELECTED_COL, linewidth=2.2 * TEXT_SCALE,
                         marker="o", markersize=4 * TEXT_SCALE, markerfacecolor=SELECTED_COL,
                         markeredgecolor=SELECTED_COL, zorder=5)
        handles.append(line)
        legend_labels.append(selected_code)

    target_handle = None
    if target_series is not None:
        target_handle, = ax.plot(x, target_series, color=TARGET_PURPLE, linewidth=2 * TEXT_SCALE,
                                  linestyle="--", zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_xlim(-0.5, n_periods - 0.5)
    _apply_axes_style(ax, y_max, y_step)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier, 0))

    reversed_handles = list(reversed(handles))
    reversed_labels = list(reversed(legend_labels))
    if target_handle is not None:
        reversed_handles.append(target_handle)
        reversed_labels.append(f"Target: {target_raw}")
    legend = fig.legend(
        reversed_handles, reversed_labels,
        loc="lower left",
        bbox_to_anchor=(_content_left, legend_bottom, _content_width, LEGEND_HEIGHT),
        bbox_transform=fig.transFigure,
        mode="expand",
        ncol=len(reversed_handles),
        fontsize=9 * TEXT_SCALE,
        frameon=True,
        borderaxespad=0,
        labelcolor=AXIS_LABEL_COL,
    )
    legend.get_frame().set_facecolor(CARD_BG)
    legend.get_frame().set_edgecolor(LEGEND_BORDER)
    legend.get_frame().set_linewidth(0.8 * TEXT_SCALE)

    table_values = []
    if selected_y is not None:
        table_values.extend(v for v in selected_y if not np.isnan(v))
    table_values.extend(v for v in means if not np.isnan(v))
    table_values.extend(v for v in medians if not np.isnan(v))
    table_mean = float(np.mean(np.abs(table_values))) if table_values else 0.0
    table_decimals = _sig_fig_decimals(table_mean)

    def _row_cells(values):
        return [
            "n/a" if i < n_pad else _format_value(v, base.format_modifier, table_decimals)
            for i, v in enumerate(values)
        ]

    row_labels = []
    cell_text = []
    if selected_y is not None:
        row_labels.append(selected_code or "Selected")
        cell_text.append(_row_cells(selected_y))
    row_labels.append("Mean")
    cell_text.append(_row_cells(means))
    row_labels.append("Median")
    cell_text.append(_row_cells(medians))

    ax_table.axis("off")
    table = ax_table.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=month_labels,
        cellLoc="center",
        rowLoc="center",
        colLoc="center",
        loc="upper center",
        bbox=[0.0, 0.0, 1.0, 1.0],
    )
    fig.canvas.draw()
    _style_table(table, selected_y is not None, n_pad, ax_table)

    return _fig_to_bytes(fig)
