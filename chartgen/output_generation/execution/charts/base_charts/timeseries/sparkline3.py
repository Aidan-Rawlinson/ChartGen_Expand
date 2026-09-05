"""Base Chart, TimeSeries, sparkline variant. Composite widget: a
"count/12" months-with-data label sits immediately before the sparkline;
the sparkline always shows a fixed 12-month window, working backwards
from the most recent period (older months are dropped if there are more
than 12, and the window is padded with "no data" months at the start if
there are fewer than 12). The sparkline draws two lines, the scope's
median per period and the Selected unit's own value per period. Any
period where the median is missing is filled in with a flat, dotted grey
line (and matching grey shading) held at the nearest known median
height, so the median line always spans the full width even with gaps;
the submission line is left exactly as before (nothing extra is drawn if
it has no data at all). Finishing (right-hand) values for both series
are labelled in their own reserved space so they can never be clipped
off. After the sparkline, two small trend badges show whether the
submission and the median increased, decreased, stayed the same (within
0.5% of each other), or can't be compared (not applicable) between the
first and last period of the 12-month window. No axes, ticks,
gridlines, legend or title, so it renders cleanly at very small sizes.
Peer-group layers are ignored."""

import io
import math
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.transforms as mtransforms

MEDIAN_COL      = "#7CB9E8"
SUBMISSION_COL  = "#C12958"
NEUTRAL_COL     = "#9AA5AF"

EMU_PER_INCH = 914400
MM_IN_INCHES = 1 / 25.4

TEXT_SCALE = 5

INNER_GAP_IN = (0.015 + 2 * MM_IN_INCHES) * 2 / 3 * TEXT_SCALE
OUTER_GAP_IN = (2 * MM_IN_INCHES) / 3 * TEXT_SCALE

# The sparkline always shows this many months, working backwards from the
# most recent period.
PERIOD_WINDOW = 12

# Dotted/dashed style shared by the submission's internal-gap bridges and
# the median's missing-data placeholder line, so both read as "no data
# here" in a consistent way.
GAP_DASH_PATTERN = (0, (1 * TEXT_SCALE, 2.4 * TEXT_SCALE))

# The grey missing-data placeholder line under the median (not the pink
# submission gap-bridges above, which keep the pattern/width as-is) is
# drawn thinner, with dashes and gaps a third the length of the general
# pattern - i.e. three times as frequent over the same distance.
NEUTRAL_DASH_PATTERN = (0, (1 * TEXT_SCALE / 3, 2.4 * TEXT_SCALE / 3))
NEUTRAL_LINE_WIDTH = 0.5 * TEXT_SCALE


def _text_width_inches(text, fontsize, dpi=100):
    if not text:
        return 0.0
    fig = plt.figure(figsize=(1, 1), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    t = ax.text(0, 0, text, fontsize=fontsize)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = t.get_window_extent(renderer=renderer)
    width_in = bbox.width / dpi
    plt.close(fig)
    return width_in


# The whole chart's content starts this far in from the true left edge of
# the canvas, so nothing drawn right at the start risks being cropped by
# the canvas boundary itself.
CONTENT_LEFT_INSET_IN = 1.2 * MM_IN_INCHES * TEXT_SCALE

# Any circle badge that sits flush against the edge of its own small
# section needs a little padding on that edge too, or its outline stroke
# (which straddles the geometric edge) gets clipped by the section's own
# axes boundary. Applied on both edges of a section so it stays visually
# centred.
CIRCLE_EDGE_PAD_IN = 0.5 * MM_IN_INCHES * TEXT_SCALE

# Has-data indicator ("count/12" label only, no icon), drawn immediately
# before the sparkline. The text box is sized tightly to "12/12" - the
# longest this label can ever be - rather than a generous guess, so
# there's no dead space between the number and the start of the
# sparkline. CIRCLE_EDGE_PAD_IN is reused here as a small left inset so
# the text doesn't sit flush against the canvas edge. Font size is a
# fixed constant, kept identical to RIGHT_LABEL_FONTSIZE below so the
# "count/12" label reads at the same size as the median/submission text.
HASDATA_TEXT_FONTSIZE = 7 * TEXT_SCALE
HASDATA_TEXT_SAMPLE_TEXT = "12/12"


def _hasdata_section_width_in():
    """Width of the has-data section, measured rather than guessed.

    A function, not a module constant, because _text_width_inches measures
    against whatever font is currently in force, and the font is not known
    at import time - ChartGen sets it around each render, from the open
    workfile's own setting. Computed at import this would bake in whatever
    font happened to be in force then, which is a different one, and the
    reserved space would be wrong by however much the two fonts differ.
    "Median: 100%" at these sizes spans about 2.9in in Calibri against
    3.5in in matplotlib's default, so the error is not subtle: the label
    either overruns into the next section or leaves dead space the
    sparkline never gets back.
    """
    return CIRCLE_EDGE_PAD_IN + _text_width_inches(HASDATA_TEXT_SAMPLE_TEXT, HASDATA_TEXT_FONTSIZE)

# Finishing-value labels, drawn in their own reserved space right after
# the sparkline so they're never at risk of being clipped off-canvas.
# This section is a FIXED width, sized once from representative sample
# text rather than from whatever the current chart's actual values
# happen to be - a missing value just leaves that half of the space
# blank rather than the layout reflowing around it. This is what keeps
# every chart in a table column lining up regardless of which rows have
# data and which don't.
RIGHT_LABEL_FONTSIZE = 7 * TEXT_SCALE
RIGHT_LABEL_PAD_IN = 1.0 * MM_IN_INCHES * TEXT_SCALE
RIGHT_LABEL_SAMPLE_TEXT = "Median: 100%"


def _right_label_width_in():
    """Fixed width of the finishing-label section, measured per render.

    A function rather than a module constant for the reason given on
    _hasdata_section_width_in: the font is not known at import time. Fixed
    still means fixed for a given render - it is sized from the sample text
    above, never from this chart's actual values - which is what keeps a
    column of these charts lining up.
    """
    return _text_width_inches(RIGHT_LABEL_SAMPLE_TEXT, RIGHT_LABEL_FONTSIZE) + RIGHT_LABEL_PAD_IN

# Trend badges (submission, then median), drawn after the labels. Spaced
# well apart both from the labels and from each other, with padding on
# both edges of the section so neither badge's outline clips against the
# section's own boundary.
TREND_BADGE_RADIUS_IN = 1.7 * MM_IN_INCHES * TEXT_SCALE
# TREND_SECTION_WIDTH_IN (the layout footprint reserved for this section,
# which the sparkline/labels widths are all calculated against) is kept
# at its original size, based on the ORIGINAL gap - so changing the
# second badge's position doesn't reflow anything else in the chart.
# TREND_BADGE_GAP_IN (the gap actually used to place the second badge)
# is set to 60% of that original 6mm gap.
TREND_BADGE_GAP_ORIGINAL_IN = 6.0 * MM_IN_INCHES * TEXT_SCALE
TREND_BADGE_GAP_IN = TREND_BADGE_GAP_ORIGINAL_IN * 0.6
TREND_SECTION_WIDTH_IN = 2 * CIRCLE_EDGE_PAD_IN + 4 * TREND_BADGE_RADIUS_IN + TREND_BADGE_GAP_ORIGINAL_IN
TREND_LINEWIDTH = 0.6 * TEXT_SCALE

# How close the first and last values of a trend need to be, relative to
# whichever of the two has the larger magnitude, to be drawn as "same"
# (an "=" badge) rather than increased/decreased.
TREND_SAME_TOLERANCE = 0.005

# The has-data indicator sits right up against the sparkline, so its own
# gap is much tighter than the gap used between the other sections - and
# tighter still than it used to be, per a specific request to close that
# particular gap by 75% (i.e. keep only a quarter of it). The gap before
# the trend badges is wider than the standard section gap, to put clear
# air between the finishing values and the first badge.
#
# A later fix corrected a bug that had been inflating the has-data-to-
# sparkline gap by roughly 2 inches (it was measuring the whole figure's
# tight bounding box instead of just the sparkline's own). A small
# amount of that removed space - about a fifth of it - is deliberately
# added back in below as RESTORED_VISUAL_GAP_IN, both here and before
# the value labels, so neither reads as touching its neighbour.
#
# Both HASDATA_SPARK_GAP_IN and TREND_SECTION_GAP_IN are then cut by a
# further third on top of that. Neither gap is topped back up elsewhere -
# spark_width_in is whatever inner_width_in has left after every other
# fixed section and gap, so the freed space lands in the sparkline
# automatically.
RESTORED_VISUAL_GAP_IN = 2.05 * MM_IN_INCHES * TEXT_SCALE
HASDATA_SPARK_GAP_IN = (0.15 * MM_IN_INCHES * TEXT_SCALE * 0.25 + RESTORED_VISUAL_GAP_IN) * (2 / 3)
SECTION_GAP_IN = OUTER_GAP_IN + RESTORED_VISUAL_GAP_IN
TREND_SECTION_GAP_IN = 2.2 * MM_IN_INCHES * TEXT_SCALE * (2 / 3)

# The sparkline's own start/end marker dots are drawn with clip_on=False
# so a full circle can render even when it sits right at the edge of the
# plotted data; this is how much extra clip room they get in every
# direction so they're never sliced in half.
MARKER_OVERFLOW_MARGIN_IN = 0.7 * MM_IN_INCHES * TEXT_SCALE

# If a chart is so narrow that the fixed-width side sections would leave
# the sparkline itself with no usable room, all three side sections are
# scaled down together (by the chart's own width, never by its data) so
# the sparkline keeps at least this fraction of the usable width.
MIN_SPARKLINE_FRACTION = 0.22

# The sparkline itself (the plotted line area, not the has-data/labels/
# trend sections either side of it) is drawn shorter than the full row
# height, centred vertically within that row. Reduced by 20% twice
# (0.8 * 0.8), then a further 10% off that result (* 0.9), each time
# keeping the same vertical centring.
SPARK_HEIGHT_FRACTION = 0.8 * 0.8 * 0.9


def _rgb_to_hls(r, g, b):
    """Local stand-in for colorsys.rgb_to_hls (not an allowed import)."""
    maxc, minc = max(r, g, b), min(r, g, b)
    l = (minc + maxc) / 2.0
    if minc == maxc:
        return 0.0, l, 0.0
    d = maxc - minc
    s = d / (maxc + minc) if l <= 0.5 else d / (2.0 - maxc - minc)
    rc, gc, bc = (maxc - r) / d, (maxc - g) / d, (maxc - b) / d
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2.0 + rc - bc
    else:
        h = 4.0 + gc - rc
    return (h / 6.0) % 1.0, l, s


def _hls_to_rgb(h, l, s):
    """Local stand-in for colorsys.hls_to_rgb (not an allowed import)."""
    if s == 0.0:
        return l, l, l
    m2 = l * (1.0 + s) if l <= 0.5 else l + s - (l * s)
    m1 = 2.0 * l - m2

    def _component(hue):
        hue %= 1.0
        if hue < 1 / 6:
            return m1 + (m2 - m1) * hue * 6.0
        if hue < 0.5:
            return m2
        if hue < 2 / 3:
            return m1 + (m2 - m1) * (2 / 3 - hue) * 6.0
        return m1

    return _component(h + 1 / 3), _component(h), _component(h - 1 / 3)


def _shade(hex_colour, lightness_delta, saturation_delta=0.0):
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = _rgb_to_hls(r, g, b)
    l = min(1.0, max(0.0, l + lightness_delta))
    s = min(1.0, max(0.0, s + saturation_delta))
    return _hls_to_rgb(h, l, s)


MEDIAN_LINE_COL = _shade(MEDIAN_COL, -0.22, 0.10)


def _format_number(value, format_modifier):
    if value is None:
        return ""
    if format_modifier == "P":
        return f"{value:,.0f}%"
    if format_modifier == "C":
        return f"£{value:,.0f}"
    return f"{value:,.0f}"


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _window_align(values, window=PERIOD_WINDOW):
    """Slice to the most recent `window` entries, or left-pad with None
    so there are always exactly `window` entries with the most recent
    one last. Working backwards from the end month is the point: older
    history beyond the window is dropped, and a short history is padded
    out as "no data" months rather than compressed or stretched."""
    values = list(values) if values else []
    n = len(values)
    if n >= window:
        return values[-window:]
    return [None] * (window - n) + values


def _ffill_bfill(values):
    """Nearest-neighbour fill: each None takes the last known value
    before it; any leading Nones (before the first known value) take the
    first known value instead. Returns None back if nothing is known at
    all, since there is then no height to carry forward or back."""
    if not any(v is not None for v in values):
        return None
    filled = list(values)
    last_known = None
    for i, v in enumerate(filled):
        if v is not None:
            last_known = v
        elif last_known is not None:
            filled[i] = last_known
    first_known = next(v for v in values if v is not None)
    for i, v in enumerate(filled):
        if v is None:
            filled[i] = first_known
    return filled


def _known_runs(known_mask):
    """Contiguous (start, end_inclusive) index ranges where known_mask is
    True."""
    runs = []
    n = len(known_mask)
    i = 0
    while i < n:
        if not known_mask[i]:
            i += 1
            continue
        j = i
        while j < n and known_mask[j]:
            j += 1
        runs.append((i, j - 1))
        i = j
    return runs


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
                color=color, linewidth=0.8 * TEXT_SCALE, linestyle=GAP_DASH_PATTERN,
                dash_capstyle="round", zorder=1.5,
            )


def _draw_gradient_fill(ax, xs, ys, baseline, top_colour, fill_zorder=0, img_zorder=0, alpha=0.48):
    if len(xs) < 2:
        return
    bottom_colour = (1.0, 1.0, 1.0)
    fade = mcolors.LinearSegmentedColormap.from_list("fade", [bottom_colour, top_colour])
    gradient = np.linspace(0, 1, 256).reshape(-1, 1)
    poly = ax.fill_between(xs, ys, baseline, color="none", zorder=fill_zorder)
    im = ax.imshow(gradient, extent=[xs[0], xs[-1], baseline, max(ys)],
                    origin="lower", aspect="auto", cmap=fade, alpha=alpha,
                    zorder=img_zorder)
    im.set_clip_path(poly.get_paths()[0], transform=ax.transData)


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
    # Only this ax's own rendered content (e.g. clip_on=False overflow
    # markers) should influence the margin - not the whole figure's, or
    # unrelated sections drawn earlier (like the has-data indicator to
    # its left) get mistaken for overflow and shove this axes across.
    tight = ax.get_tightbbox(renderer).transformed(fig.dpi_scale_trans.inverted())

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


def _section_axes(fig, w_in, h_in, left_in, bottom_in, width_in, height_in, equal_aspect=True):
    """A small sub-axes for a fixed-size section. With equal_aspect, a
    1:1 inch-based data coordinate system means a radius specified in
    inches draws as a true circle regardless of the section's own aspect
    ratio; text-only sections don't need that constraint."""
    ax = fig.add_axes([left_in / w_in, bottom_in / h_in, width_in / w_in, height_in / h_in])
    ax.set_xlim(0, width_in)
    ax.set_ylim(0, height_in)
    if equal_aspect:
        ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("none")
    return ax


def _count_with_data(values):
    return sum(1 for v in values if v is not None)


def _draw_has_data_indicator(ax, cy, count_with_data, total):
    has_data = count_with_data > 0
    colour = SUBMISSION_COL if has_data else NEUTRAL_COL
    ax.text(
        CIRCLE_EDGE_PAD_IN, cy,
        f"{count_with_data}/{total}", ha="left", va="center",
        fontsize=HASDATA_TEXT_FONTSIZE, color=colour, zorder=3,
    )


def _draw_right_labels(ax_labels, median_val, submission_val, submission_code, format_modifier):
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
    for (text, colour, _), y in zip(entries, y_positions):
        ax_labels.text(0.0, y, text, transform=ax_labels.transAxes, color=colour,
                        fontsize=RIGHT_LABEL_FONTSIZE,
                        ha="left", va="center")


def _trend(first, last):
    """"same" covers both an exact match and a near-match: first and
    last are treated as equal if they're within TREND_SAME_TOLERANCE
    (0.5%) of the larger of the two values' magnitudes, not just when
    they're identical."""
    if first is None or last is None:
        return "n/a"
    try:
        f, l = float(first), float(last)
    except (TypeError, ValueError):
        return "n/a"
    if f != f or l != l:  # NaN check
        return "n/a"
    denom = max(abs(f), abs(l))
    if denom == 0.0 or abs(f - l) <= TREND_SAME_TOLERANCE * denom:
        return "same"
    return "increased" if l > f else "decreased"


def _triangle_points(cx, cy, size, pointing_up):
    tip_y = cy + size if pointing_up else cy - size
    base_y = cy - size * 0.55 if pointing_up else cy + size * 0.55
    half_w = size * 0.85
    return np.array([
        [cx, tip_y],
        [cx - half_w, base_y],
        [cx + half_w, base_y],
    ])


def _draw_dash(ax, cx, cy, radius, colour):
    """A single short dash, used on the trend badge when there isn't
    both a start and a finish value to compare."""
    half_w = radius * 0.5
    ax.plot([cx - half_w, cx + half_w], [cy, cy], color=colour,
            linewidth=1.0 * TEXT_SCALE, solid_capstyle="round", zorder=3)


def _draw_equals(ax, cx, cy, radius, colour="white"):
    """An "=" glyph: two short horizontal bars, for a trend that's
    unchanged (or near enough) between the first and last value."""
    bar_half_w, bar_half_h = radius * 0.55, radius * 0.12
    bar_offset = radius * 0.32
    for dy in (-bar_offset, bar_offset):
        rect = mpatches.Rectangle(
            (cx - bar_half_w, cy + dy - bar_half_h),
            2 * bar_half_w, 2 * bar_half_h,
            facecolor=colour, edgecolor="none", zorder=3,
        )
        ax.add_patch(rect)


def _draw_trend_badge(ax, cx, cy, radius, trend, series_colour):
    if trend == "n/a":
        # Stays in the series' own colour (submission pink / median blue)
        # rather than switching to neutral grey, so it's still obvious at
        # a glance which badge is which. A single dash stands in for "no
        # start/finish values to compare".
        circle = plt.Circle((cx, cy), radius, facecolor="none",
                             edgecolor=series_colour, linewidth=TREND_LINEWIDTH, zorder=2)
        ax.add_patch(circle)
        _draw_dash(ax, cx, cy, radius, series_colour)
        return

    circle = plt.Circle((cx, cy), radius, facecolor=series_colour,
                         edgecolor=series_colour, linewidth=TREND_LINEWIDTH, zorder=2)
    ax.add_patch(circle)

    glyph_size = radius * 0.55
    if trend == "increased":
        tri = mpatches.Polygon(_triangle_points(cx, cy, glyph_size, True),
                                closed=True, facecolor="white", edgecolor="none", zorder=3)
        ax.add_patch(tri)
    elif trend == "decreased":
        tri = mpatches.Polygon(_triangle_points(cx, cy, glyph_size, False),
                                closed=True, facecolor="white", edgecolor="none", zorder=3)
        ax.add_patch(tri)
    else:  # "same"
        _draw_equals(ax, cx, cy, radius, colour="white")


def sparkline3(population_layers: list, width_emu=2736215, height_emu=684054, tweaks=""):
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
    inner_left_in = h_border_in + CONTENT_LEFT_INSET_IN
    inner_bottom_in = v_border_in
    inner_width_in = w - inner_left_in - h_border_in
    inner_height_in = h - 2 * v_border_in

    fig = plt.figure(figsize=(w, h))

    # --- Always a fixed 12-month window, working backwards from the end
    # month: truncate older history, pad a short history with "no data"
    # months at the start. -----------------------------------------------
    medians_natural = [ps.median for ps in metric.period_stats] if metric.period_stats else []
    medians_raw = _window_align(medians_natural)
    median_known_mask = [v is not None for v in medians_raw]
    any_median_known = any(median_known_mask)

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

    submission_natural = submission_unit.values if submission_unit else []
    submission_full = _window_align(submission_natural)
    has_submission = any(v is not None for v in submission_full)
    submission_values = [float(v) if v is not None else float("nan") for v in submission_full]
    submission_values_present = [v for v in submission_full if v is not None]

    x = np.arange(PERIOD_WINDOW)

    # --- Layout: has-data indicator | sparkline | value labels | trend ----
    # Every section here is a FIXED width, set once from the module-level
    # constants (or, for the two side-shrink cases below, scaled by a
    # single ratio that depends only on the chart's own overall size).
    # None of these widths depend on which values happen to be present
    # this time - a missing median or submission just leaves blank space
    # in its slot rather than the layout reflowing, which is what keeps a
    # column of these lining up in a table.
    format_modifier = getattr(base, "format_modifier", None)
    submission_code = submission_unit.unit_code if submission_unit else None
    median_last = medians_raw[-1] if median_known_mask[-1] else None
    submission_last = submission_full[-1]

    hasdata_width_in = _hasdata_section_width_in()
    trend_width_in = TREND_SECTION_WIDTH_IN
    right_label_width_in = _right_label_width_in()

    # hasdata-spark uses the tight HASDATA_SPARK_GAP_IN; spark-labels uses
    # the normal SECTION_GAP_IN; labels-trend uses the wider
    # TREND_SECTION_GAP_IN.
    total_side_gap_in = HASDATA_SPARK_GAP_IN + SECTION_GAP_IN + TREND_SECTION_GAP_IN
    spark_width_in = (
        inner_width_in - hasdata_width_in - trend_width_in - right_label_width_in
        - total_side_gap_in
    )
    min_spark_width_in = inner_width_in * MIN_SPARKLINE_FRACTION
    if spark_width_in < min_spark_width_in:
        # Only happens for a chart that's simply too narrow for all the
        # fixed-size furniture to fit at once - a function of this
        # chart's own overall width, never of which values it happens to
        # be showing this time.
        deficit = min_spark_width_in - spark_width_in
        side_total = hasdata_width_in + trend_width_in + right_label_width_in
        if side_total > 0:
            shrink_ratio = max(0.0, 1 - deficit / side_total)
            hasdata_width_in *= shrink_ratio
            trend_width_in *= shrink_ratio
            right_label_width_in *= shrink_ratio
        spark_width_in = (
            inner_width_in - hasdata_width_in - trend_width_in - right_label_width_in
            - total_side_gap_in
        )

    hasdata_left_in = inner_left_in
    spark_left_in = hasdata_left_in + hasdata_width_in + HASDATA_SPARK_GAP_IN
    labels_left_in = spark_left_in + spark_width_in + SECTION_GAP_IN
    trend_left_in = labels_left_in + right_label_width_in + TREND_SECTION_GAP_IN

    # --- Has-data indicator ("count/12") -----------------------------------
    count_with_data = _count_with_data(submission_full)
    if hasdata_width_in > 0:
        ax_hd = _section_axes(fig, w, h, hasdata_left_in, inner_bottom_in,
                               hasdata_width_in, inner_height_in)
        _draw_has_data_indicator(ax_hd, inner_height_in / 2, count_with_data, PERIOD_WINDOW)

    # --- Sparkline ------------------------------------------------------------
    # Drawn at SPARK_HEIGHT_FRACTION of the full row height, centred
    # vertically within that row - the has-data indicator, value labels
    # and trend badges either side of it keep the full row height.
    spark_height_in = inner_height_in * SPARK_HEIGHT_FRACTION
    spark_bottom_in = inner_bottom_in + (inner_height_in - spark_height_in) / 2

    ax = fig.add_axes([
        spark_left_in / w, spark_bottom_in / h,
        spark_width_in / w, spark_height_in / h,
    ])

    all_values = []
    if any_median_known:
        all_values.extend(v for v in medians_raw if v is not None)
    if submission_values_present:
        all_values.extend(submission_values_present)

    axis_bottom, axis_top = None, None
    if all_values:
        data_min, data_max = min(all_values), max(all_values)
        data_range = data_max - data_min
        buffer = data_range * 0.125 if data_range > 0 else max(abs(data_max), 1) * 0.1
        axis_bottom, axis_top = data_min - buffer, data_max + buffer

    if any_median_known:
        baseline = axis_bottom if axis_bottom is not None else min(
            v for v in medians_raw if v is not None)
        filled_medians = _ffill_bfill(medians_raw)

        # Grey backdrop across the full width, standing in for any month
        # with no median: a flat, dotted line held at the nearest known
        # height, shaded the same way the real (blue) line is - but at
        # half the fill intensity, and with a thinner, finer-dashed line.
        _draw_gradient_fill(ax, x, filled_medians, baseline, NEUTRAL_COL,
                             fill_zorder=0, img_zorder=0, alpha=0.24)
        ax.plot(x, filled_medians, color=NEUTRAL_COL, linewidth=NEUTRAL_LINE_WIDTH,
                linestyle=NEUTRAL_DASH_PATTERN, dash_capstyle="round", zorder=1)

        # Real (blue) line and shading, only where the median is actually
        # known, layered on top of the grey backdrop.
        for start, end in _known_runs(median_known_mask):
            run_x = x[start:end + 1]
            run_y = medians_raw[start:end + 1]
            _draw_gradient_fill(ax, run_x, run_y, baseline, _shade(MEDIAN_COL, -0.01, 0.04),
                                 fill_zorder=0.4, img_zorder=0.4)
            ax.plot(run_x, run_y, color=MEDIAN_LINE_COL, linewidth=1.0 * TEXT_SCALE,
                    zorder=1.5, solid_capstyle="round")

    if has_submission:
        _draw_internal_gap_bridges(ax, x, submission_full, SUBMISSION_COL)
        ax.plot(x, submission_values, color=SUBMISSION_COL, linewidth=0.8 * TEXT_SCALE,
                zorder=2, solid_capstyle="round")
        ax.plot(x, submission_values, linestyle="none", marker="o",
                markersize=1.333 * TEXT_SCALE, color=SUBMISSION_COL, zorder=3)

    if any_median_known:
        median_dot_y = [v if k else float("nan") for v, k in zip(medians_raw, median_known_mask)]
        ax.plot([x[0], x[-1]], [median_dot_y[0], median_dot_y[-1]], linestyle="none",
                marker="o", markersize=2.667 * TEXT_SCALE, color=MEDIAN_LINE_COL, zorder=2,
                clip_on=False)
    if has_submission:
        ax.plot([x[0], x[-1]], [submission_values[0], submission_values[-1]],
                linestyle="none", marker="o", markersize=2.667 * TEXT_SCALE,
                color=SUBMISSION_COL, zorder=4, clip_on=False)

    ax.axis("off")
    ax.margins(x=0.02)
    if axis_bottom is not None:
        ax.set_ylim(axis_bottom, axis_top)

    # The clip box is padded beyond the section's own strict bounds so
    # the clip_on=False start/end marker dots can render as full circles
    # even when they sit right at the edge of the plotted data, instead
    # of being sliced off by the section boundary.
    _inset_axes_to_fit(
        fig, ax,
        spark_left_in - MARKER_OVERFLOW_MARGIN_IN, spark_bottom_in - MARKER_OVERFLOW_MARGIN_IN,
        spark_width_in + 2 * MARKER_OVERFLOW_MARGIN_IN, spark_height_in + 2 * MARKER_OVERFLOW_MARGIN_IN,
    )

    # --- Finishing values, in their own reserved space --------------------
    if right_label_width_in > 0:
        ax_labels = _section_axes(fig, w, h, labels_left_in, inner_bottom_in,
                                   right_label_width_in, inner_height_in, equal_aspect=False)
        _draw_right_labels(ax_labels, median_last,
                            submission_last if has_submission else None,
                            submission_code, format_modifier)

    # --- Trend badges: submission then median, first period vs last -------
    if trend_width_in > 0:
        ax_tr = _section_axes(fig, w, h, trend_left_in, inner_bottom_in,
                               trend_width_in, inner_height_in)
        cy = inner_height_in / 2
        badge1_cx = CIRCLE_EDGE_PAD_IN + TREND_BADGE_RADIUS_IN
        badge2_cx = badge1_cx + 2 * TREND_BADGE_RADIUS_IN + TREND_BADGE_GAP_IN

        submission_trend = _trend(submission_full[0], submission_full[-1])
        median_trend = _trend(medians_raw[0], medians_raw[-1])

        _draw_trend_badge(ax_tr, badge1_cx, cy, TREND_BADGE_RADIUS_IN,
                           submission_trend, SUBMISSION_COL)
        _draw_trend_badge(ax_tr, badge2_cx, cy, TREND_BADGE_RADIUS_IN,
                           median_trend, MEDIAN_LINE_COL)

    return _fig_to_bytes(fig)
