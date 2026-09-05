"""Base Chart, TimeSeries. Mean and median reference lines across every period, a highlighted line per subsequent population layer, and a per-period table of Selected, Mean and Median values beneath the chart. Plot, key and table each occupy a fixed non-overlapping band, sized in centimetres of the placed picture. The table's row-label column fills a gutter that the plot area starts after, so the picture's border and the plot's left edge match column_ci_full when the two are stacked on one page. CI report styling."""

import io
import math
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.collections as mcollections

# Every blue in this file is a tint of BASE_BLUE. The greys and the other
# hues are their own colours.
BASE_BLUE       = "#0070C0"
SELECTED_COL    = "#DA291C"
MEAN_COL        = "#009639"
MEDIAN_COL      = "#78BE20"
BORDER_GREY     = "#87929C"   # plot panel, table cells and table outline
HEADER_TEXT_COL = "#2F3A45"
AXIS_LABEL_COL  = "#515C65"
BENCHMARK_COL   = "#9B30FF"

PEER_ALPHAS = [1.0, 0.7, 0.5, 0.35]

EMU_PER_INCH = 914400
CM_PER_INCH  = 2.54

TEXT_SCALE = 5

# Point sizes as they appear on the A4 page. Multiplied by TEXT_SCALE at
# the point of use. Shared, value for value, with column_ci_full.
FS_KEY      = 7.0
FS_AXIS     = 6.5
FS_ROWLABEL = 6.5
FS_TICK     = 6.0
FS_TABLE    = 6.0
FS_EMPTY    = 10.0

# Centimetres of the placed picture. Converted to a figure fraction from
# the figure's own size, so they stay the same physical distance if the
# picture is resized.
BORDER_CM       = 0.30
GUTTER_CM       = 1.15
BAND_GAP_CM     = 0.12
KEY_HEIGHT_CM   = 0.45
TABLE_ROW_CM    = 0.45
CORNER_CM       = 0.15
CARD_CORNER_CM  = 0.12   # the picture itself, a tighter curve than the blocks on it
HATCH_SPACING_CM = 0.12

TICK_PAD_PT = 4.0
HATCH_LW_PT = 0.5
BORDER_LW_PT = 0.50

# Gaps inside the key, in multiples of its own font size, so TEXT_SCALE
# cancels out of them.
KEY_COLUMN_SPACING  = 1.4
KEY_HANDLE_TEXT_PAD = 0.5

# Dashes across the full plot height on the divider between the padded and
# the real months.
DIVIDER_DASHES = 16

# The benchmark line. Matplotlib multiplies a dash pattern by the line's
# width before drawing it, and that width already carries TEXT_SCALE, so
# the pattern is written plain and gets its scaling from there.
BENCHMARK_LW_PT = 1.33
BENCHMARK_DASH  = (2.8, 1.2)

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


OTHER_COL          = BASE_BLUE
CARD_BG            = _tint(BASE_BLUE, 0.06)   # the picture background
HEADER_BG          = _tint(BASE_BLUE, 0.35)
ROWLABEL_BG        = _tint(BASE_BLUE, 0.05)
GREYED_HATCH_COL   = _tint(BORDER_GREY, 0.29)
GREYED_DIVIDER_COL = _tint(BORDER_GREY, 0.40)

# Gridlines are a tint of the border grey, so the line work is one family.
GRID_COL = _tint(BORDER_GREY, 0.21)

# One surface colour, shared by the plot panel and the table's data cells.
PLOT_BG       = _tint(CARD_BG, 0.20)
TABLE_CELL_BG = PLOT_BG



def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _cm_to_inches(cm):
    """A distance in centimetres of the placed picture, in inches of the
    inflated figure this file is asked to draw."""
    return (cm / CM_PER_INCH) * TEXT_SCALE


def _cm_to_fraction(cm, extent_inches):
    return _cm_to_inches(cm) / extent_inches


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _rounded_patch(fig, left_frac, bottom_frac, width_frac, height_frac,
                   facecolor, edgecolor="none", zorder=0, add=True,
                   radius_cm=CORNER_CM):
    """A rounded rectangle placed by figure fraction but drawn in inches, so
    the corner radius is the same in both directions rather than stretched
    by the figure's aspect."""
    fig_w, fig_h = fig.get_size_inches()
    patch = mpatches.FancyBboxPatch(
        (left_frac * fig_w, bottom_frac * fig_h),
        width_frac * fig_w, height_frac * fig_h,
        boxstyle=mpatches.BoxStyle("Round", pad=0.0,
                                   rounding_size=_cm_to_inches(radius_cm)),
        mutation_scale=1.0,
        facecolor=facecolor, edgecolor=edgecolor,
        linewidth=0.0 if edgecolor == "none" else BORDER_LW_PT * TEXT_SCALE,
        zorder=zorder,
    )
    patch.set_transform(fig.dpi_scale_trans)
    if add:
        fig.add_artist(patch)
    return patch


def _draw_card(fig):
    """The picture's own background, as a rounded card rather than the figure
    patch. The figure itself stays transparent, so the corners let whatever the
    picture is placed on show through."""
    fig.patch.set_facecolor("none")
    _rounded_patch(fig, 0.0, 0.0, 1.0, 1.0, facecolor=CARD_BG, zorder=-1,
                   radius_cm=CARD_CORNER_CM)


def _hatch_rect(owner, fig, x0_in, y0_in, x1_in, y1_in, colour, zorder,
                clip_patch=None, fill=None):
    """Diagonal lines drawn one by one, in inches of the figure, over the
    given rectangle.

    Matplotlib's own hatch repeats at a fixed rate per figure inch, so on a
    canvas inflated by TEXT_SCALE it comes out that many times finer and
    shrinks to a flat grey wash when the picture is placed. No hatch string
    is sparse enough to correct for it, so the lines are drawn directly at a
    spacing measured on the page. Each runs at 45 degrees, which makes
    trimming it to the rectangle's own width a matter of matching the y step
    to the x step.
    """
    height = y1_in - y0_in
    spacing = _cm_to_inches(HATCH_SPACING_CM)

    if fill is not None:
        panel = mpatches.Rectangle((x0_in, y0_in), x1_in - x0_in, height,
                                   facecolor=fill, edgecolor="none", zorder=zorder)
        panel.set_transform(fig.dpi_scale_trans)
        if clip_patch is not None:
            panel.set_clip_path(clip_patch)
        owner.add_artist(panel)

    segments = []
    start = x0_in - height
    while start < x1_in:
        left = max(start, x0_in)
        right = min(start + height, x1_in)
        if right > left:
            segments.append([(left, y0_in + (left - start)),
                             (right, y0_in + (right - start))])
        start += spacing

    lines = mcollections.LineCollection(
        segments, colors=colour, linewidths=HATCH_LW_PT * TEXT_SCALE, zorder=zorder,
    )
    lines.set_transform(fig.dpi_scale_trans)
    if clip_patch is not None:
        lines.set_clip_path(clip_patch)
    owner.add_artist(lines)


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


def _axis_decimals(y_max, step, format_modifier):
    """Zero decimals where the ticks read distinctly, one where they would
    not. A low axis at zero decimals prints 0, 0, 1, 1, 2."""
    count = int(round(y_max / step))
    ticks = [i * step for i in range(count + 1)]
    labels = [_format_value(t, format_modifier, 0) for t in ticks]
    return 0 if len(set(labels)) == len(labels) else 1


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
    """This chart's own tweaks grammar: caret-separated key:value pairs, or a bare flag with no colon. Two are read. benchmark:N or benchmark:median draws a reference line, and target: is accepted as a synonym for it. 12m forces a fixed 12-month axis, most recent months rightmost, missing early months padded as an empty hatched band."""
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


def _empty_chart(width_emu, height_emu):
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    _draw_card(fig)
    ax.set_facecolor("none")
    ax.text(0.5, 0.5, "No data", ha="center", va="center", color=AXIS_LABEL_COL,
            fontsize=FS_EMPTY * TEXT_SCALE)
    ax.axis("off")
    return _fig_to_bytes(fig)


def _style_table(fig, table, has_selected_row, n_pad, ax_table):
    table.auto_set_font_size(False)

    renderer = fig.canvas.get_renderer()
    dpi = fig.dpi
    fig_w, fig_h = fig.get_size_inches()
    cells = list(table.get_celld().values())

    # Rounded outer corners on the block as a whole rather than on each cell:
    # clip everything to a rounded rectangle covering the table, then draw the
    # outline on top so the boundary curves rather than being cut off square.
    boxes = [c.get_window_extent(renderer) for c in cells]
    left = min(b.x0 for b in boxes) / dpi
    right = max(b.x1 for b in boxes) / dpi
    bottom = min(b.y0 for b in boxes) / dpi
    top = max(b.y1 for b in boxes) / dpi
    clip = _rounded_patch(fig, left / fig_w, bottom / fig_h,
                          (right - left) / fig_w, (top - bottom) / fig_h,
                          facecolor="none", zorder=0, add=False)

    row_colours = []
    if has_selected_row:
        row_colours.append(SELECTED_COL)
    row_colours.append(MEAN_COL)
    row_colours.append(MEDIAN_COL)

    padded_cells = []
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(BORDER_GREY)
        cell.set_linewidth(BORDER_LW_PT * TEXT_SCALE)
        # Cell.__init__ turns clipping off and builds its text the same
        # way, and matplotlib ignores a clip path while that is false, so
        # both have to be switched back on for the rounding to take.
        cell.set_clip_on(True)
        cell.get_text().set_clip_on(True)
        cell.set_clip_path(clip)
        cell.get_text().set_clip_path(clip)
        if row == 0:
            cell.set_facecolor(HEADER_BG)
            cell.set_text_props(color=HEADER_TEXT_COL, fontweight="bold",
                                fontsize=FS_TICK * TEXT_SCALE)
        elif col == -1:
            cell.set_facecolor(ROWLABEL_BG)
            cell.set_text_props(fontweight="bold", fontsize=FS_ROWLABEL * TEXT_SCALE,
                                color=row_colours[row - 1])
        elif n_pad and col < n_pad:
            # Filled and hatched underneath instead of by the cell itself, so
            # the cell's own text still reads over the top of the lines.
            cell.set_facecolor("none")
            cell.set_text_props(color=AXIS_LABEL_COL, fontsize=FS_TABLE * TEXT_SCALE,
                                style="italic")
            padded_cells.append(cell)
        else:
            cell.set_facecolor(TABLE_CELL_BG)
            cell.set_text_props(color=AXIS_LABEL_COL, fontsize=FS_TABLE * TEXT_SCALE)

    hatch_zorder = table.get_zorder() - 0.1
    for cell in padded_cells:
        box = cell.get_window_extent(renderer)
        _hatch_rect(ax_table, fig, box.x0 / dpi, box.y0 / dpi, box.x1 / dpi, box.y1 / dpi,
                    GREYED_HATCH_COL, hatch_zorder, clip_patch=clip, fill=TABLE_CELL_BG)

    _rounded_patch(fig, left / fig_w, bottom / fig_h,
                   (right - left) / fig_w, (top - bottom) / fig_h,
                   facecolor="none", edgecolor=BORDER_GREY,
                   zorder=table.get_zorder() + 2)


def line_ci_full(population_layers: list, width_emu=5486400, height_emu=3086100, tweaks=""):
    # No font.family set here, deliberately. ChartGen sets it around the
    # call, from the workfile's own setting, so this file inherits it.
    # Setting it here at all - at import or in an rc_context - would
    # override that choice and pin this one chart to a different typeface
    # from every other. See base_charts/CLAUDE.md.
    return _draw(population_layers, width_emu, height_emu, tweaks)


def _draw(population_layers, width_emu, height_emu, tweaks):
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
    benchmark_raw = tweak_values.get("benchmark") or tweak_values.get("target")
    benchmark_series = None
    if benchmark_raw:
        if benchmark_raw.lower() == "median":
            benchmark_series = medians
        else:
            try:
                benchmark_series = np.full(n_real, float(benchmark_raw))
            except ValueError:
                benchmark_series = None

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
    benchmark_series = _apply_padding(benchmark_series, n_pad, window_size)

    n_periods = len(means)
    x = np.arange(n_periods)
    month_labels = [_month_label(l) for l in padded_labels] + \
                   [_month_label(p.period_label) for p in windowed_periods]

    all_values = list(means[~np.isnan(means)]) + list(medians[~np.isnan(medians)])
    if selected_y is not None:
        all_values.extend(list(selected_y[~np.isnan(selected_y)]))
    for pm, _, _ in peer_series:
        all_values.extend(list(pm[~np.isnan(pm)]))
    if benchmark_series is not None:
        all_values.extend(list(benchmark_series[~np.isnan(benchmark_series)]))

    max_plotted = max(all_values) if all_values else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)

    w, h = _size_to_inches(width_emu, height_emu)
    fig = plt.figure(figsize=(w, h))
    _draw_card(fig)

    # --- Layout. Fixed centimetres of the placed picture, converted to
    # figure fractions here. The gutter carries the y-axis numbers above and
    # the table's row labels below; the plot and the table's data columns
    # both start where it ends, which is also where column_ci_full's plot
    # starts, so the pair aligns on the page.
    row_labels = []
    if selected_y is not None:
        row_labels.append(selected_code or "Selected")
    row_labels.append("Mean")
    row_labels.append("Median")

    border_x = _cm_to_fraction(BORDER_CM, w)
    border_y = _cm_to_fraction(BORDER_CM, h)
    gutter   = _cm_to_fraction(GUTTER_CM, w)
    band_gap = _cm_to_fraction(BAND_GAP_CM, h)
    key_h    = _cm_to_fraction(KEY_HEIGHT_CM, h)
    table_h  = _cm_to_fraction(TABLE_ROW_CM, h) * (len(row_labels) + 1)

    content_left  = border_x + gutter
    content_width = 1.0 - border_x - content_left

    table_bottom = border_y
    key_bottom   = table_bottom + table_h + band_gap
    plot_bottom  = key_bottom + key_h + band_gap
    plot_top     = 1.0 - border_y
    plot_height  = plot_top - plot_bottom

    if content_width <= 0:
        raise ValueError(
            "line_ci_full: no width left for the plot. BORDER_CM and GUTTER_CM "
            "together exceed the picture width."
        )
    if plot_height <= 0:
        raise ValueError(
            "line_ci_full: no height left for the plot. BORDER_CM, TABLE_ROW_CM, "
            "KEY_HEIGHT_CM and BAND_GAP_CM together exceed the picture height."
        )

    ax = fig.add_axes([content_left, plot_bottom, content_width, plot_height])
    ax.set_facecolor("none")
    plot_panel = _rounded_patch(fig, content_left, plot_bottom, content_width, plot_height,
                                facecolor=PLOT_BG, edgecolor=BORDER_GREY, zorder=0)

    # The table's axes covers the data columns only. Matplotlib fits a table
    # to its bbox on those columns alone and hangs the row labels off the
    # left, which is what puts the labels in the gutter and every data column
    # under the month it describes.
    ax_table = fig.add_axes([content_left, table_bottom, content_width, table_h])
    ax_table.set_facecolor("none")
    ax_table.axis("off")

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

    benchmark_handle = None
    if benchmark_series is not None:
        benchmark_handle, = ax.plot(x, benchmark_series, color=BENCHMARK_COL,
                                    linewidth=BENCHMARK_LW_PT * TEXT_SCALE,
                                    linestyle=(0, BENCHMARK_DASH), zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_xlim(-0.5, n_periods - 0.5)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(y_step))
    ax.yaxis.set_major_formatter(
        _axis_formatter(base.format_modifier, _axis_decimals(y_max, y_step, base.format_modifier))
    )
    # No separate line at zero: the plot panel's own border runs along the
    # same edge, so one even frame does that job on all four sides.
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, color=GRID_COL, linewidth=0.5 * TEXT_SCALE, zorder=0)
    ax.xaxis.grid(False)
    ax.tick_params(axis="y", labelsize=FS_AXIS * TEXT_SCALE, colors=AXIS_LABEL_COL,
                   length=0, pad=TICK_PAD_PT * TEXT_SCALE)
    ax.tick_params(axis="x", length=0)

    # The gridlines at zero and at the axis maximum sit exactly on the
    # panel border, so they would draw that line a second time. Matched on
    # position rather than index, in case the locator hands back a tick
    # outside the view.
    for loc, gridline in zip(ax.get_yticks(), ax.yaxis.get_gridlines()):
        if loc <= 0 or loc >= y_max:
            gridline.set_visible(False)

    divider = None
    if n_pad:
        # Dashes are counted across the plot's own height, so the count holds
        # at any picture size. Being canvas-derived the period already carries
        # the TEXT_SCALE factor and must not be multiplied again. Matplotlib
        # multiplies a dash pattern by the line's width before drawing it, so
        # the period is divided by that width to survive the trip.
        divider_lw = 1 * TEXT_SCALE
        period_pt = (plot_height * h * 72.0) / DIVIDER_DASHES / divider_lw
        divider = ax.axvline(n_pad - 0.5, color=GREYED_DIVIDER_COL, linewidth=divider_lw,
                             linestyle=(0, (period_pt * 0.6, period_pt * 0.4)), zorder=0.6)

    for artist in list(ax.get_ygridlines()) + [divider]:
        if artist is not None:
            artist.set_clip_path(plot_panel)

    reversed_handles = list(reversed(handles))
    reversed_labels = list(reversed(legend_labels))
    if benchmark_handle is not None:
        reversed_handles.append(benchmark_handle)
        reversed_labels.append(f"Benchmark: {benchmark_raw}")
    # No frame. The plot's border above and the table's below do that job,
    # so the entries pack to their own width and centre in the band rather
    # than being spread across it.
    legend = fig.legend(
        reversed_handles, reversed_labels,
        loc="center",
        bbox_to_anchor=(content_left, key_bottom, content_width, key_h),
        bbox_transform=fig.transFigure,
        ncol=len(reversed_handles),
        fontsize=FS_KEY * TEXT_SCALE,
        frameon=False,
        borderaxespad=0,
        borderpad=0,
        columnspacing=KEY_COLUMN_SPACING,
        handletextpad=KEY_HANDLE_TEXT_PAD,
        labelcolor=AXIS_LABEL_COL,
    )

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

    cell_text = []
    if selected_y is not None:
        cell_text.append(_row_cells(selected_y))
    cell_text.append(_row_cells(means))
    cell_text.append(_row_cells(medians))

    table = ax_table.table(
        cellText=cell_text,
        colLabels=month_labels,
        cellLoc="center",
        colLoc="center",
        loc="upper center",
        bbox=[0.0, 0.0, 1.0, 1.0],
    )
    # Row labels are added by hand rather than through the rowLabels argument.
    # That argument puts the column under matplotlib's own auto-width, which
    # measures the label text and overrides any width set here.
    row_label_width = gutter / content_width
    cell_height = next(iter(table.get_celld().values())).get_height()
    for i, label in enumerate(row_labels):
        table.add_cell(i + 1, -1, width=row_label_width, height=cell_height,
                       text=label, facecolor=ROWLABEL_BG, loc="center")

    # Data columns take an equal share of the bbox they are fitted to. The
    # row-label column hangs off the left of it, so its width is set as the
    # gutter's share of that same span, which lands it on the picture's
    # border.
    for (row, col), cell in table.get_celld().items():
        cell.set_width(row_label_width if col == -1 else 1.0 / n_periods)

    fig.canvas.draw()
    _style_table(fig, table, selected_y is not None, n_pad, ax_table)

    if n_pad:
        # The empty months on the plot get the same hatching as their cells,
        # drawn into the axes so it sits under the data lines, and clipped to
        # the rounded panel so it does not square off its corners.
        dpi = fig.dpi
        left_disp, bottom_disp = ax.transData.transform((-0.5, 0))
        right_disp, top_disp = ax.transData.transform((n_pad - 0.5, y_max))
        _hatch_rect(ax, fig, left_disp / dpi, bottom_disp / dpi,
                    right_disp / dpi, top_disp / dpi,
                    GREYED_HATCH_COL, 0.5, clip_patch=plot_panel)

    return _fig_to_bytes(fig)
