"""
sparkline1.py
Base Chart -- TimeSeries, sparkline variant. Draws exactly two lines: the
population median across each period, and the Selected unit's own
submission value across each period. No axes, ticks, gridlines, legend or
title -- built to render cleanly at very small sizes (e.g. inside a table
cell or alongside a headline figure).

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) -- no report_context or any other runtime object.

population_layers[0] is always the scope and supplies the median line.
population_layers[1:] are highlight layers; the "Selected" layer supplies
the submission value line. Any other (peer group) layer is ignored by
this sparkline variant -- it only ever draws these two lines.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import colorsys
import numpy as np
import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font. SVG text is kept as
# real text, not glyph outlines -- see line_ci_full's own comment for
# the full reasoning.
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.transforms as mtransforms

MEDIAN_COL      = "#7CB9E8"   # base blue the median fill/line are derived from
SUBMISSION_COL  = "#C12958"

EMU_PER_INCH = 914400
MM_IN_INCHES = 1 / 25.4

# PowerPoint SVG-text-compression workaround -- see line_ci_full's own
# TEXT_SCALE comment for the full reasoning. Must match the system
# layer's own CHART_RENDER_SCALE (assembly_engine.py) exactly. Applied
# below to INNER_GAP_IN/OUTER_GAP_IN too, not just fontsize/linewidth --
# both are fixed *physical-inch* offsets from the axes edge, so without
# this they'd shrink to a much smaller proportion of the chart once this
# chart is drawn on the inflated canvas and shrunk back down.
TEXT_SCALE = 5

# Two separate, independently tunable physical gaps either side of an end
# label -- both fixed inches, not fractions of the axes' own width (see
# the note on GAP_IN's old single-value version, further down, for why
# fractional offsets don't work here). Reading outward from the plot
# area toward the canvas edge: plot area -> INNER_GAP_IN -> label text ->
# OUTER_GAP_IN -> border -> canvas edge.
INNER_GAP_IN = (0.015 + 2 * MM_IN_INCHES) * 2 / 3 * TEXT_SCALE   # label's near edge to plot area
OUTER_GAP_IN = (2 * MM_IN_INCHES) / 3 * TEXT_SCALE                # label's far edge to the border


def _shade(hex_colour, lightness_delta, saturation_delta=0.0):
    """Adjust a hex colour's lightness and saturation in HLS space, keeping
    its hue fixed. This avoids the washed-out/grey look that comes from
    blending straight toward white or black in RGB."""
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1.0, max(0.0, l + lightness_delta))
    s = min(1.0, max(0.0, s + saturation_delta))
    return colorsys.hls_to_rgb(h, l, s)


# The median line is drawn noticeably darker/richer than the raw base
# colour; the fill gradient runs from a touch darker than that at the top
# to a light (but still clearly blue, not grey) tint at the bottom.
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
    """None stays None; a NaN (a gap left by _blank_chart's caller
    converting a missing month for plotting) also becomes None -- neither
    should ever reach _add_end_labels' own "is not None" check, which
    would otherwise let a NaN through and print the literal text "nan"."""
    if v is None:
        return None
    return None if v != v else v  # v != v is true only for NaN


def _add_end_labels(fig, ax, side, median_val, submission_val,
                     submission_code, format_modifier):
    """Draw the median/submission end labels a fixed INNER_GAP_IN inches
    from the axes' own left or right edge (side='left' or 'right') -- not
    an axes-fraction offset, so the gap stays a constant physical size no
    matter how _inset_axes_to_fit ends up sizing the axes. The other gap
    (label to border, OUTER_GAP_IN) isn't set here -- it's added as extra
    reserved margin in _inset_axes_to_fit itself, since it sits on the far
    side of the label from the axes and isn't expressible as an anchor
    offset the way this one is. They sit evenly spaced top-to-bottom as a
    centred pair, regardless of where the lines themselves start or
    finish; whichever value is higher is placed on top. Labels are bold
    throughout, with no spacing around the colon."""
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
        entries.sort(key=lambda e: e[2], reverse=True)  # highest value on top
        y_positions = [0.70, 0.30]   # centred as a group
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
    """
    A dotted connector across each run of missing (None) periods that has
    real data both immediately before and immediately after it -- a
    leading or trailing gap (nothing on one side to connect to) gets no
    bridge, same as the solid line's own plain break there. Distinct from
    the solid submission line, which already leaves a genuine gap at any
    None (matplotlib skips a NaN automatically) -- this draws directly
    across that gap, from the last known point to the next known one,
    dotted rather than solid, to visually distinguish "bridged over a
    missing period" from an actual reported value.
    """
    n = len(values_raw)
    i = 0
    while i < n:
        if values_raw[i] is not None:
            i += 1
            continue
        start = i
        while i < n and values_raw[i] is None:
            i += 1
        end = i  # first index after the run, exclusive
        if start > 0 and end < n and values_raw[start - 1] is not None and values_raw[end] is not None:
            ax.plot(
                [x[start - 1], x[end]], [values_raw[start - 1], values_raw[end]],
                color=color, linewidth=0.8 * TEXT_SCALE, linestyle=(0, (1 * TEXT_SCALE, 2.4 * TEXT_SCALE)),
                dash_capstyle="round", zorder=1.5,
            )
        # start == 0 (leading) or end == n (trailing): left as a plain
        # break, nothing to bridge to on the missing side.


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg",
                facecolor="none", edgecolor="none", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _inset_axes_to_fit(fig, ax, box_left_in, box_bottom_in, box_width_in, box_height_in):
    """
    Reserve real space inside the visualisation's own box (not the full
    figure -- see sparkline1's own border reservation) for whatever draws
    outside the axes (the end labels and the large end-markers, both
    clip_on=False) -- rather than cropping the saved file down to content
    (bbox_inches="tight"), which changes the file's own dimensions away
    from the figsize the caller actually requested (width_emu/height_emu).
    A Base Chart's contract is to render at exactly the requested size;
    the returned SVG must carry that size itself, not rely on whatever
    inserts it later (a table-cell splice, a PowerPoint picture frame) to
    stretch it back to the right shape -- that stretch is non-uniform
    whenever the crop's own aspect ratio doesn't match the requested one,
    which is what was squishing the end-label text horizontally.

    Insets on all four sides, not just left/right -- a large end-marker
    can just as easily overflow the box vertically as a label can
    horizontally (confirmed: the median end-marker breaching the box's
    top edge), and the same measure-then-reserve mechanism handles both
    without needing separate marker-specific logic.

    box_left_in/box_bottom_in/box_width_in/box_height_in describe the
    visualisation's own box in figure-inches (absolute, not fraction) --
    the border reserved around it is untouched by anything in here;
    everything drawn must stay inside this box, never the border.

    Renders once to measure the true extent of everything currently drawn
    (fig.get_tightbbox, the same call table_cardtile.py uses for its own
    chart-cell precision fix -- Architecture Decision 30), then insets the
    axes by the full overflow found relative to the box's own edges on
    whichever side(s) it occurs, so a second render places the same
    content entirely inside the box. One correction pass, not iterated to
    convergence -- shrinking the axes slightly changes how much of the
    end-markers' data-space position relative to the axis limits sits
    outside the box, but by a second-order amount not worth chasing here.
    The end-labels' own gap from the axes edge (INNER_GAP_IN, a fixed
    number of inches) is unaffected by this, by design. The other gap
    (label to border, OUTER_GAP_IN) IS this function's concern -- it's
    added on top of the measured overflow below, so the reserved margin
    is deliberately larger than the bare minimum needed to fit the label,
    leaving genuine empty space between the label's far edge and the
    border rather than the label sitting flush against it.

    No cap on the reserved margin -- an earlier version capped this at
    30% of the box per side, to guard against a genuinely tiny target
    canvas inverting left/right and collapsing the axes. In practice that
    never gets hit at realistic sizes and just made the margin harder to
    reason about, so it's gone; if a future canvas turns out small enough
    to need protecting again, that's a sign to revisit this, not silently
    reintroduce a cap.

    The clip applied at the end here (to the box, not the full figure --
    the border must stay empty) is a pure safety net for anything that
    still overflows the box after this reservation -- with no cap, that
    should be rare, but it costs nothing to keep. The clip is applied only
    after this measurement, not before -- doing it earlier would make
    fig.get_tightbbox() see the already-clipped (smaller) extent instead
    of the artist's true, unclipped size, silently defeating the overflow
    calculation above.
    """
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
    """Sparkline: submission value line and population median line, no axes/legend/title."""
    if not population_layers:
        return _blank_chart(width_emu, height_emu)

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        return _blank_chart(width_emu, height_emu)

    # Reserve a transparent border around the actual visualisation: 5% of
    # the original height_emu top and bottom. Left/right use a sixth of
    # that (the end labels sit there, and the gap from plot area to label
    # already widened separately -- this border is just the last sliver
    # from label to the true canvas edge, kept small deliberately).
    # Both are based on height_emu (not width_emu), so they stay a uniform
    # physical thickness regardless of the chart's own aspect ratio -- the
    # drawn chart (lines, fill, end labels, everything _inset_axes_to_fit
    # does) occupies a centred inner box of
    # (width_emu - 2*(0.05/6)*height_emu) by (0.9*height_emu); the returned
    # SVG itself still stays exactly width_emu x height_emu, matching the
    # Base Chart contract -- only the border is left empty.
    v_border_emu = 0.05 * height_emu
    h_border_emu = v_border_emu / 6
    # Guard against a degenerate aspect ratio where the border would
    # consume the whole width -- keep at least a sliver of inner canvas
    # rather than a negative/zero-width inner box.
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

    # "Any data" -- the same test line_has_data.py uses -- not "every
    # value present". A partially-missing series (some months None) is
    # still real, drawable data: those months become a genuine gap in the
    # line (matplotlib skips over a NaN automatically, in both the line
    # and its markers), not a reason to suppress the whole line. An
    # earlier version required every value non-None or drew nothing at
    # all -- meant to stop a None reaching min()/max() below (a real
    # crash: "'<' not supported between instances of 'NoneType' and
    # 'float'"), but it over-corrected: a single missing month blanked an
    # otherwise-complete submission line entirely, silently, for what is
    # the common case, not a rare one. Only a genuinely all-None series is
    # now treated as no submission at all.
    submission_values_raw = submission_unit.values if submission_unit else None
    has_submission = bool(submission_values_raw) and any(v is not None for v in submission_values_raw)
    submission_values = None
    submission_values_present = []  # non-None entries only, for the axis-range calc below
    if has_submission:
        submission_values = [float(v) if v is not None else float("nan") for v in submission_values_raw]
        submission_values_present = [v for v in submission_values_raw if v is not None]

    # Collect every value that will actually be plotted so the 10%/90%
    # buffer reflects the true visual range, not just the median line.
    all_values = []
    if has_medians:
        all_values.extend(medians)
    if submission_values_present:
        all_values.extend(submission_values_present)

    # Work out the axis limits up front (10% buffer top and bottom) so the
    # fill can be drawn all the way down to the bottom of the chart.
    axis_bottom, axis_top = None, None
    if all_values:
        data_min, data_max = min(all_values), max(all_values)
        data_range = data_max - data_min
        # Buffer sized so the lowest value sits at 10% of the axis height
        # and the highest sits at 90% -- i.e. data occupies the middle 80%.
        buffer = data_range * 0.125 if data_range > 0 else max(abs(data_max), 1) * 0.1
        axis_bottom, axis_top = data_min - buffer, data_max + buffer

    if has_medians:
        baseline = axis_bottom if axis_bottom is not None else min(medians)
        top_colour = _shade(MEDIAN_COL, -0.01, 0.04)  # halfway between the lighter and darker versions tried, still fading to white below
        bottom_colour = (1.0, 1.0, 1.0)               # washes out to pure white at the bottom
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
        # Small marker on every month, red line only.
        ax.plot(x, submission_values, linestyle="none", marker="o",
                markersize=1.333 * TEXT_SCALE, color=SUBMISSION_COL, zorder=3)

    # Larger start/end markers on both lines -- clip_on=False so
    # _inset_axes_to_fit can reserve room to draw the full circle even
    # when it sits right at (or just past) the plot edge.
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
