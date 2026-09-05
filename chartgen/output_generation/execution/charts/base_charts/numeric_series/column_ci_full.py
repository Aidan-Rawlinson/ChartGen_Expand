"""Base Chart, NumericSeries. Ranked descending column chart, Selected organisation highlighted, median reference line, key as a vertical stack to the right of the plot. Layout is built from fixed centimetre measurements of the placed picture, so the border and the plot area's left edge match line_ci_full when the two are stacked on one page. CI report styling. Units with no data are excluded entirely rather than plotted as zero."""

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
import matplotlib.transforms as mtransforms
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath


# Every blue in this file is a tint of BASE_BLUE. The greys and the other
# hues are their own colours.
BASE_BLUE     = "#0070C0"
SELECTED_RED  = "#DA291C"
MEDIAN_GREEN  = "#78BE20"
AXIS_GREY     = "#515C65"
BORDER_GREY   = "#87929C"   # plot panel and key panel
BENCHMARK_COL = "#9B30FF"

EMU_PER_INCH = 914400
CM_PER_INCH  = 2.54

TEXT_SCALE = 5

# Point sizes as they appear on the A4 page. Multiplied by TEXT_SCALE at
# the point of use. Shared with line_ci_full except FS_KEY, which is a
# point smaller here because this key is a narrow panel beside the plot
# rather than a band across it.
FS_KEY     = 6.0
FS_AXIS    = 6.5
FS_CALLOUT = 6.5
FS_TICK    = 6.0
FS_EMPTY   = 10.0

# Centimetres of the placed picture. Converted to a figure fraction from
# the figure's own size, so they stay the same physical distance if the
# picture is resized.
BORDER_CM    = 0.30
GUTTER_CM    = 1.15
KEY_WIDTH_CM = 3.20
KEY_GAP_CM   = 0.25
XLABEL_CM    = 0.35
CORNER_CM    = 0.15
CARD_CORNER_CM = 0.12   # the picture itself, a tighter curve than the blocks on it
LABEL_PAD_CM = 0.04

# Above this many organisations the codes below the bars collide, so all
# are hidden except the Selected one. Bars are never dropped.
MAX_LABELLED_UNITS = 20

# The benchmark line. Matplotlib multiplies a dash pattern by the line's
# width before drawing it, and that width already carries TEXT_SCALE, so
# the pattern is written plain and gets its scaling from there.
BENCHMARK_LW_PT = 1.33
BENCHMARK_DASH  = (2.8, 1.2)

# The key's swatches, in multiples of its own font size.
KEY_HANDLE_LENGTH = 1.6

BAR_GAP_PT = 4.0
BORDER_LW_PT = 0.50
TICK_PAD_PT = 4.0


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


OTHER_BLUE = BASE_BLUE
CARD_BG    = _tint(BASE_BLUE, 0.06)   # the picture background

# Gridlines are a tint of the border grey, so the line work is one family.
GRID_GREY = _tint(BORDER_GREY, 0.21)

# One surface colour, shared by the plot panel and the key panel.
PLOT_BG = _tint(CARD_BG, 0.20)

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


def _rounded_panel(fig, left_frac, bottom_frac, width_frac, height_frac,
                   facecolor, edgecolor="none", zorder=0, radius_cm=CORNER_CM):
    """A rounded rectangle placed by figure fraction but drawn in inches, so
    the corner radius is the same in both directions rather than stretched
    by the figure's aspect."""
    fig_w, fig_h = fig.get_size_inches()
    radius = _cm_to_inches(radius_cm)
    patch = mpatches.FancyBboxPatch(
        (left_frac * fig_w, bottom_frac * fig_h),
        width_frac * fig_w, height_frac * fig_h,
        boxstyle=mpatches.BoxStyle("Round", pad=0.0, rounding_size=radius),
        mutation_scale=1.0,
        facecolor=facecolor, edgecolor=edgecolor,
        linewidth=0.0 if edgecolor == "none" else BORDER_LW_PT * TEXT_SCALE,
        zorder=zorder,
    )
    patch.set_transform(fig.dpi_scale_trans)
    fig.add_artist(patch)
    return patch


def _draw_card(fig):
    """The picture's own background, as a rounded card rather than the figure
    patch. The figure itself stays transparent, so the corners let whatever the
    picture is placed on show through."""
    fig.patch.set_facecolor("none")
    _rounded_panel(fig, 0.0, 0.0, 1.0, 1.0, facecolor=CARD_BG, zorder=-1,
                   radius_cm=CARD_CORNER_CM)


def _tight_label(fig, text, x_display, y_display, colour, fontsize_pt, x_align="center"):
    """Text with a translucent panel behind it, sized to the glyph outlines
    rather than the font's line box. Matplotlib's own text bbox covers the
    full ascender-to-descender line height, which stands off above and below
    a string of digits; TextPath gives the real ink extent instead."""
    dpi = fig.dpi
    x_in = x_display / dpi
    y_in = y_display / dpi

    # No family given, so this measures the ambient font - the same one the
    # text itself will be drawn in. Naming a family here would size the
    # panel to one font's glyphs and draw the text in another.
    prop = FontProperties(weight="bold", size=fontsize_pt)
    ink = TextPath((0, 0), text, prop=prop).get_extents()
    width_in = ink.width / 72.0
    height_in = ink.height / 72.0

    if x_align == "center":
        left_in = x_in - width_in / 2.0
    elif x_align == "right":
        left_in = x_in - width_in
    else:
        left_in = x_in

    pad_in = _cm_to_inches(LABEL_PAD_CM)
    panel = mpatches.Rectangle(
        (left_in - pad_in, y_in - pad_in),
        width_in + 2 * pad_in, height_in + 2 * pad_in,
        facecolor="white", alpha=0.6, edgecolor="none", zorder=9,
    )
    panel.set_transform(fig.dpi_scale_trans)
    fig.add_artist(panel)

    fig.text(left_in - ink.x0 / 72.0, y_in - ink.y0 / 72.0, text,
             transform=fig.dpi_scale_trans, ha="left", va="baseline",
             fontsize=fontsize_pt, color=colour, fontweight="bold", zorder=10)


def _format_number(value, format_modifier, decimals=0):
    if value is None:
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
    labels = [_format_number(t, format_modifier, 0) for t in ticks]
    return 0 if len(set(labels)) == len(labels) else 1


def _axis_formatter(format_modifier, decimals):
    return mticker.FuncFormatter(lambda v, _: _format_number(v, format_modifier, decimals))


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
    """This chart's own tweaks grammar: caret-separated key:value pairs. One key is read, benchmark:N or benchmark:median, drawing a reference line at that value. target: is accepted as a synonym for it."""
    result = {}
    if not tweaks:
        return result
    for part in tweaks.split("^"):
        if ":" not in part:
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


def _selected_identity(population_layers):
    selected_layer = next((l for l in population_layers if l.population_label == "Selected"), None)
    if selected_layer is None or not selected_layer.units:
        return None, None, None
    unit = selected_layer.units[0]
    code = unit.unit_code or unit.unit_id
    return unit.unit_id, code, unit.values[0]


def _empty_chart(width_emu, height_emu):
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    _draw_card(fig)
    ax.set_facecolor(PLOT_BG)
    ax.text(0.5, 0.5, "No data", ha="center", va="center", color=AXIS_GREY,
            fontsize=FS_EMPTY * TEXT_SCALE)
    ax.axis("off")
    return _fig_to_bytes(fig)


def column_ci_full(population_layers: list, width_emu=5486400, height_emu=3429000, tweaks=""):
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
    if not base.metric_stats:
        return _empty_chart(width_emu, height_emu)
    ms = base.metric_stats[0]

    units = sorted(
        (u for u in base.units if u.values[0] is not None),
        key=lambda u: -u.values[0],
    )
    if not units:
        return _empty_chart(width_emu, height_emu)

    w, h = _size_to_inches(width_emu, height_emu)
    fig = plt.figure(figsize=(w, h))
    _draw_card(fig)

    # --- Layout. Fixed centimetres of the placed picture, converted to
    # figure fractions here. The plot's left edge is border plus gutter,
    # matching line_ci_full so the two align when stacked.
    border_x = _cm_to_fraction(BORDER_CM, w)
    border_y = _cm_to_fraction(BORDER_CM, h)
    gutter   = _cm_to_fraction(GUTTER_CM, w)
    key_w    = _cm_to_fraction(KEY_WIDTH_CM, w)
    key_gap  = _cm_to_fraction(KEY_GAP_CM, w)
    xlabel_h = _cm_to_fraction(XLABEL_CM, h)

    plot_left   = border_x + gutter
    plot_right  = 1.0 - border_x - key_w - key_gap
    plot_bottom = border_y + xlabel_h
    plot_top    = 1.0 - border_y
    plot_width  = plot_right - plot_left
    plot_height = plot_top - plot_bottom

    if plot_width <= 0:
        raise ValueError(
            "column_ci_full: no width left for the plot. BORDER_CM, GUTTER_CM, "
            "KEY_WIDTH_CM and KEY_GAP_CM together exceed the picture width."
        )
    if plot_height <= 0:
        raise ValueError(
            "column_ci_full: no height left for the plot. BORDER_CM and "
            "XLABEL_CM together exceed the picture height."
        )

    ax = fig.add_axes([plot_left, plot_bottom, plot_width, plot_height])
    ax.set_facecolor("none")
    plot_panel = _rounded_panel(fig, plot_left, plot_bottom, plot_width, plot_height,
                                facecolor=PLOT_BG, edgecolor=BORDER_GREY, zorder=0)

    codes  = [u.unit_code for u in units]
    values = [u.values[0] for u in units]
    x = np.arange(len(codes))

    sel_unit_id, sel_code, sel_val = _selected_identity(population_layers)
    sel_idx = next((i for i, u in enumerate(units) if u.unit_id == sel_unit_id), None) \
        if sel_unit_id is not None else None

    key_values = [v for v in (sel_val, ms.mean, ms.median) if v is not None]
    key_mean = float(np.mean(np.abs(key_values))) if key_values else 0.0
    key_decimals = _sig_fig_decimals(key_mean)

    colours = [SELECTED_RED if i == sel_idx else OTHER_BLUE for i in range(len(units))]

    slot_width = 0.6
    bars = ax.bar(x, values, color=colours, width=slot_width, zorder=2)

    tweak_values = _parse_tweaks(tweaks)
    benchmark_raw = tweak_values.get("benchmark") or tweak_values.get("target")
    benchmark_value = None
    if benchmark_raw:
        if benchmark_raw.lower() == "median":
            benchmark_value = ms.median
        else:
            try:
                benchmark_value = float(benchmark_raw)
            except ValueError:
                benchmark_value = None

    candidates = [v for v in values if v is not None]
    if ms.median is not None:
        candidates.append(ms.median)
    if benchmark_value is not None:
        candidates.append(benchmark_value)
    max_plotted = max(candidates) if candidates else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)

    ax.set_xlim(-0.6, len(codes) - 0.4)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(y_step))
    ax.yaxis.set_major_formatter(
        _axis_formatter(base.format_modifier, _axis_decimals(y_max, y_step, base.format_modifier))
    )

    median_line = None
    if ms.median is not None:
        median_line = ax.axhline(ms.median, color=MEDIAN_GREEN, linewidth=2 * TEXT_SCALE, zorder=3)

    benchmark_line = None
    if benchmark_value is not None:
        benchmark_line = ax.axhline(benchmark_value, color=BENCHMARK_COL,
                                    linewidth=BENCHMARK_LW_PT * TEXT_SCALE,
                                    linestyle=(0, BENCHMARK_DASH), zorder=4)

    ax.set_xticks(x)
    tick_labels = ax.set_xticklabels(codes, rotation=0, ha="center",
                                     fontsize=FS_TICK * TEXT_SCALE)
    label_all = len(units) <= MAX_LABELLED_UNITS
    for i, lbl in enumerate(tick_labels):
        if i == sel_idx:
            lbl.set_color(SELECTED_RED)
            lbl.set_fontweight("bold")
        elif label_all:
            lbl.set_color(AXIS_GREY)
        else:
            lbl.set_visible(False)

    ax.tick_params(axis="y", labelsize=FS_AXIS * TEXT_SCALE, colors=AXIS_GREY,
                   length=0, pad=TICK_PAD_PT * TEXT_SCALE)
    ax.tick_params(axis="x", length=0, pad=TICK_PAD_PT * TEXT_SCALE)
    ax.yaxis.grid(True, color=GRID_GREY, linewidth=0.5 * TEXT_SCALE)
    # No separate line at zero: the plot panel's own border runs along the
    # same edge, so one even frame does that job on all four sides.
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)

    # The gridlines at zero and at the axis maximum sit exactly on the
    # panel border, so they would draw that line a second time. Matched on
    # position rather than index, in case the locator hands back a tick
    # outside the view.
    for loc, gridline in zip(ax.get_yticks(), ax.yaxis.get_gridlines()):
        if loc <= 0 or loc >= y_max:
            gridline.set_visible(False)

    # Everything drawn inside the plot is clipped to the rounded panel, so
    # nothing squares off the corners the panel has rounded.
    for artist in list(bars) + list(ax.get_ygridlines()) + [median_line, benchmark_line]:
        if artist is not None:
            artist.set_clip_path(plot_panel)

    mean_label   = f"Mean: {_format_number(ms.mean, base.format_modifier, decimals=key_decimals)}" if ms.mean is not None else "Mean: -"
    median_label = f"Median: {_format_number(ms.median, base.format_modifier, decimals=key_decimals)}" if ms.median is not None else "Median: -"
    sel_value_text = _format_number(sel_val, base.format_modifier, decimals=key_decimals) if sel_val is not None else "n/a"
    handles = [
        mpatches.Patch(color=SELECTED_RED, label=f"{sel_code or 'Selected'}: {sel_value_text}"),
        mpatches.Patch(color=OTHER_BLUE, label="Other providers"),
        plt.Line2D([0], [0], color=MEDIAN_GREEN, linewidth=2 * TEXT_SCALE, label=median_label),
        plt.Line2D([0], [0], color="none", label=mean_label),
    ]
    if benchmark_line is not None:
        handles.append(plt.Line2D([0], [0], color=BENCHMARK_COL,
                                  linewidth=BENCHMARK_LW_PT * TEXT_SCALE,
                                  linestyle=(0, BENCHMARK_DASH),
                                  label=f"Benchmark: {benchmark_raw}"))

    # A single column filling the reserved KEY_WIDTH_CM, its own height only,
    # centred on the plot area's vertical middle.
    legend = fig.legend(
        handles, [hd.get_label() for hd in handles],
        loc="center left",
        bbox_to_anchor=(plot_right + key_gap, plot_bottom, key_w, plot_height),
        bbox_transform=fig.transFigure,
        mode="expand",
        ncol=1,
        fontsize=FS_KEY * TEXT_SCALE,
        frameon=False,
        borderaxespad=0,
        borderpad=0.9,
        handlelength=KEY_HANDLE_LENGTH,
        labelspacing=0.7,
        labelcolor=AXIS_GREY,
    )
    # The key panel is drawn by the same helper as the plot panel rather
    # than by matplotlib's own legend frame. That frame carries the
    # legend.framealpha default of 0.8, which renders a hairline border at
    # 80% alpha and leaves it looking soft beside the opaque ones.
    # Measuring it also lays the figure out, which the callout labels below
    # need anyway.
    fig.canvas.draw()
    key_box = legend.get_window_extent(fig.canvas.get_renderer())
    _rounded_panel(fig,
                   key_box.x0 / (fig.dpi * w), key_box.y0 / (fig.dpi * h),
                   key_box.width / (fig.dpi * w), key_box.height / (fig.dpi * h),
                   facecolor=PLOT_BG, edgecolor=BORDER_GREY, zorder=0)

    if sel_idx is not None and sel_val is not None:
        x_disp, y_disp = ax.transData.transform((sel_idx, sel_val))
        _tight_label(
            fig,
            _format_number(sel_val, base.format_modifier, decimals=key_decimals),
            x_disp, y_disp + (BAR_GAP_PT * TEXT_SCALE / 72.0) * fig.dpi,
            SELECTED_RED, FS_CALLOUT * TEXT_SCALE, x_align="center",
        )

    if benchmark_value is not None:
        label_trans = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
        x_disp, y_disp = label_trans.transform((1.0, benchmark_value))
        _tight_label(
            fig, f"Benchmark: {benchmark_raw}",
            x_disp - (BAR_GAP_PT * TEXT_SCALE / 72.0) * fig.dpi,
            y_disp + (BAR_GAP_PT * TEXT_SCALE / 72.0) * fig.dpi,
            BENCHMARK_COL, FS_CALLOUT * TEXT_SCALE, x_align="right",
        )

    return _fig_to_bytes(fig)
