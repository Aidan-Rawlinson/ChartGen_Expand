"""
line_ci_full.py
Base Chart — TimeSeries. Mean and median reference lines across every
period, with a highlighted line per subsequent population layer (Selected
or peer group), styled to the Community Indicators chart specification
(NHS Identity palette), plus a per-period data table beneath the chart
showing the Selected, Mean and Median values for each period.

Replaces the earlier version of this chart (which reused
median_comparison_linechart's median-only logic, restyled). This version
is converted from a Custom Chart bundle the user recovered from an
earlier session (a genuinely different chart design — mean AND median
reference lines, plus an embedded per-period table — not just a restyle
of an existing built-in). Converted to the current chart_inputs contract
(width_emu/height_emu, SVG return, Calibri) from the bundle's own
pre-Decision-27/29 width/height-percent/PNG form; no other logic changed.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) — no report_context or any other runtime object. The
Selected unit's label comes from its own unit_code in the
"Selected"-labelled population layer.

population_layers[0] is always the scope and drives the mean/median
reference lines, regardless of its own label; population_layers[1:] are
highlighted on top — "Selected" as the individual unit's own trend line
(NHS Red, on top of every other series), any other label (a resolved
peer group) as that group's mean line (NHS Blue, dashed).

Values on this chart are displayed as percentages regardless of the
data's own format_modifier, per this chart's own display convention.

The table is not a separate element — it is part of this single
visualisation, sharing the one figure with the chart above it, and the
whole thing (chart + table together) is sized to width_emu/height_emu.
Chart, legend and table each occupy an explicitly reserved band of the
figure (placed by absolute figure coordinates, not by axes-relative
legend positioning), with a small fixed buffer between bands, so none of
the three can encroach on another regardless of how much content each
contains. The outer margin (top, bottom, left, right) is a single
consistent value on all four sides — a left-hand "gutter" is reserved
ahead of the axes for the y-axis tick labels and the table's row-label
column, both of which draw outside their axes' own bounding box, so
their actual visible ink lines up with the margin rather than eating
into it.

Values follow the shape's own format_modifier, the same convention every
other Base Chart uses: "P" appends "%", "C" prefixes "£", anything else
(including "N", or blank) gets no suffix at all — plain, comma-thousands
formatting. The source bundle this chart was converted from hardcoded
"always show as a percentage regardless of format_modifier" as its own
display convention; that was wrong against real data (an "N"-modifier
metric was being shown with a false "%" suffix) and has been replaced
with the standard rule.

--- "12m" tweak ---
This chart is not told the report's own period range (chart_inputs
contract — no report_context reaches a Base Chart). The report this
chart is normally used in covers a fixed 12-month year, but early in
that year the underlying data may only actually exist for the last few
months. The "12m" bare flag (no colon/value — just the literal text
"12m" somewhere in the tweaks string) tells this chart to always present
a full 12-month axis regardless of how many real periods it was actually
given: whatever real periods exist occupy the most recent (rightmost)
months, and however many months are short of 12 get synthesised at the
front as empty, hatched "no data" months. This is presentation only —
no data is invented, no real value is altered, nothing is filtered. As
real months accumulate over the year this shrinks on its own; nothing
about this logic needs revisiting as the year progresses. If given more
than 12 real periods, only the most recent 12 are shown (same "most
recent 12, working backwards" rule, no synthesis needed). Every real
per-period series (mean, median, Selected, each peer group, the target
line) is padded/trimmed identically via _apply_padding so they all stay
aligned to the same 12-month axis. The synthetic months' own labels are
calculated by stepping calendar-month-backwards from the first real
period's own label; if that label doesn't parse as "Month YYYY", padding
is skipped entirely for that render (chart still draws, just without the
synthetic months) rather than guessing.
"""

import io
import math
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font. See Architecture, SVG
# rendering methodology (Decision 27). The source bundle used Arial (the
# CI report spec's own typography) — kept as Calibri here per that
# governed decision, same as column_ci_full.
matplotlib.rcParams["font.family"] = "Calibri"
# SVG text is kept as real text, not glyph outlines -- every Base
# Chart/Table does this now. PowerPoint's own SVG compression routine
# mis-spaces individual characters when text is baked into paths, most
# visibly on decimal-heavy labels ("0.000"); real <text>, combined with
# this chart's own TEXT_SCALE below, avoids that. Set per-file, not as a
# global rcParam, so a downloaded Custom Charts bundle (this whole
# module's source, handed to an AI standalone) stays correct in
# isolation rather than silently depending on an app-level setting.
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches

SELECTED_COL   = "#DA291C"   # NHS Red - this organisation
MEAN_COL       = "#009639"   # NHS Green (dark) - mean
MEDIAN_COL     = "#78BE20"   # NHS Light Green - median
OTHER_COL      = "#005EB8"   # NHS Blue - peer groups
GRID_COL       = "#DFE6EE"   # pale grey - gridlines
BASELINE_COL   = "#2F3A45"   # dark grey - baseline
AXIS_LABEL_COL = "#5B6770"   # grey - axis tick labels
CARD_BG        = "#F0F5FC"   # outer card background (figure)
LEGEND_BORDER  = "#E6E9ED"   # light grey - legend / table border
TARGET_PURPLE  = "#9B30FF"   # bright purple - tweaks-driven target reference line, this chart's own copy (matches column_ci_full's)

# "12m" tweak — synthetic/no-data month styling. GREYED_HATCH_COL drives
# both the chart's axvspan hatch and the table's "n/a" cell hatch, so the
# two greyed regions read as the same visual concept rather than two
# unrelated design choices. GREYED_DIVIDER_COL is deliberately the same
# colour again — one muted grey standing for "inactive", not a second
# accent colour to track.
GREYED_HATCH_COL   = "#E9EDF0"
GREYED_DIVIDER_COL = "#E9EDF0"

PEER_ALPHAS = [1.0, 0.7, 0.5, 0.35]

EMU_PER_INCH = 914400

# --- PowerPoint SVG-text-compression workaround ---
# PowerPoint's own lossy compression of an embedded SVG mis-spaces
# individual characters when text is kept as real <text> (svg.fonttype
# "none", above) rather than glyph outlines -- most visible on
# decimal-heavy labels ("0.000"). The system layer
# (assembly_engine._render_chart_image) calls this chart with
# width_emu/height_emu already multiplied by a fixed factor, then places
# the result back at the real target size on the slide -- but that alone
# only inflates the drawn canvas, not any of this chart's own absolute
# point-based sizes (fontsize, linewidth, markersize, dash-pattern
# lengths), which would otherwise stay proportionally tiny relative to
# the now-bigger canvas once shrunk back down. TEXT_SCALE multiplies
# every such literal in this file to match.
#
# This number must equal the system layer's own multiplier exactly (see
# assembly_engine.py's own constant) -- not enforced in code, since Base
# Charts are standalone artefacts with no shared imports (Architecture,
# "Base Charts are outside the system boundary"). A mismatch here would
# only make this chart's own text/lines look proportionally wrong
# relative to its own canvas; it wouldn't affect any other chart.
TEXT_SCALE = 5

# --- Figure layout: one consistent outer margin on all four sides, then
# three fixed vertical bands (bottom to top: table, slim buffer, legend,
# slim buffer, chart) filling the space between. Fixed fractions (rather
# than tight_layout/gridspec auto-sizing) so the bands can never encroach
# on one another, and the outer margin reads the same on every edge.
#
# LABEL_GUTTER reserves room, ahead of the axes' left edge, for content
# that matplotlib draws outside the axes bounding box: the y-axis tick
# labels (chart) and the row-label column (table). Without it, that
# content spills left of MARGIN while nothing spills right of MARGIN on
# the other side, making the right edge look doubled by comparison. ---
MARGIN          = 0.055   # identical on top, bottom, left and right
LABEL_GUTTER    = 0.048   # reserved for y-axis tick labels / table row labels
TABLE_HEIGHT    = 0.30
BUFFER_1        = 0.025   # between table and legend - squeezed
LEGEND_HEIGHT   = 0.085
BUFFER_2        = 0.020   # between legend and chart plot area - squeezed

_content_left   = MARGIN + LABEL_GUTTER
_content_width  = 1.0 - (2 * MARGIN) - LABEL_GUTTER
_content_bottom = MARGIN
_content_top    = 1.0 - MARGIN

# "Month YYYY" parsing/stepping for the "12m" tweak's synthetic months —
# matched on the month name's first three letters, case-insensitive, the
# same recognition rule _month_label already uses for display, so
# anything this chart already displays correctly also parses correctly
# here.
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
    """Blend a colour toward white. strength=1.0 keeps the colour as-is;
    strength=0.25 keeps only a quarter of its distance from white (i.e.
    a much paler version of the same colour)."""
    r, g, b = _hex_to_rgb(hex_colour)
    r = 255 - (255 - r) * strength
    g = 255 - (255 - g) * strength
    b = 255 - (255 - b) * strength
    return _rgb_to_hex((r, g, b))


PLOT_BG          = _tint(CARD_BG, 0.25)         # plot area background, 25% of current strength
TABLE_CELL_BG    = _tint(CARD_BG, 0.25)         # table body cell background, matching the plot area
HEADER_BG        = _tint(OTHER_COL, 0.35)       # table header row, deliberately toned down
ROWLABEL_BG      = _tint("#EFF5FC", 0.6)        # table row-label background, kept a little more visible


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
    """Convert a period label such as 'June 2025' to 'Jun 25'."""
    parts = period_label.split()
    if len(parts) != 2:
        return period_label
    month_name, year = parts
    if not year.isdigit():
        return period_label
    return f"{month_name[:3]} {year[-2:]}"


def _parse_period_label(period_label):
    """
    Parse a period label of the form 'Month YYYY' (e.g. 'April 2026')
    into (year, month) ints, or None if it doesn't match that shape.
    "12m" tweak support — see _build_padding_labels.
    """
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
    """(year, month) for `steps` calendar months before the given (year, month). steps=1 is the immediately preceding month. "12m" tweak support."""
    zero_based = (year * 12 + (month - 1)) - steps
    return zero_based // 12, (zero_based % 12) + 1


def _build_padding_labels(first_real_label, n_pad):
    """
    Full 'Month YYYY' labels for n_pad synthetic periods immediately
    preceding first_real_label, oldest first. Returns None if
    first_real_label doesn't parse -- caller skips padding entirely in
    that case rather than guessing at calendar months. "12m" tweak
    support.
    """
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
    """
    Trim `arr` to its last `window_size` elements (no-op if arr is
    already that length or shorter), then prepend `n_pad` NaNs. Used to
    align every real per-period series (mean, median, Selected, each
    peer group, target) onto the same final period axis uniformly --
    "12m" tweak support, but a genuine no-op (window_size=len(arr),
    n_pad=0) whenever the tweak isn't active, so this is always safe to
    call. Returns None unchanged (some series, e.g. selected_y, are
    legitimately None).
    """
    if arr is None:
        return None
    trimmed = arr[-window_size:] if window_size < len(arr) else arr
    if n_pad:
        return np.concatenate([np.full(n_pad, np.nan), trimmed])
    return trimmed


def _format_value(value, format_modifier, decimals):
    """Standard Base Chart formatting rule: "P" appends "%", "C" prefixes
    "£", anything else (including "N", or blank) gets plain comma-thousands
    formatting with no suffix at all. `decimals` is always supplied by the
    caller (this chart's table decides it once per render, per
    _sig_fig_decimals) rather than defaulting here, since a silent default
    would let a call site forget to think about it."""
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
    """Nice-numbers axis algorithm (Heckbert-style): returns a rounded
    figure close to `value` using only 1/2/3/4/5-times-a-power-of-ten
    steps (a wider set than the classic 1/2/5 — agreed to give a snugger
    fit against real data, e.g. a step of 300 rather than jumping straight
    to 500)."""
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
    """A round y-axis maximum a little above the highest plotted value,
    with a matching 'nice' tick step. The step is derived directly from
    the padded max divided by the target band count, then the axis max is
    the smallest multiple of that step covering the padded max -- rather
    than rounding the whole range up to a coarse tier first and deriving
    the step from that afterwards, which could overshoot badly (e.g. a
    padded max of 1353 jumping all the way to 2000 rather than landing on
    1500) and didn't reliably give the target band count either. Band
    count is no longer a guarantee under this approach -- it lands close
    to target_ticks most of the time, but can come out higher or lower
    depending on where the data falls; the trade-off is a consistently
    snug axis instead."""
    if max_plotted_value <= 0:
        return 1.0, 0.2
    padded = max_plotted_value * 1.10
    raw_step = padded / target_ticks
    step = _nice_number(raw_step, round_to_nearest=True)
    y_max = math.ceil(padded / step) * step
    return y_max, step


def _parse_tweaks(tweaks: str) -> dict:
    """
    Parse this chart's own tweaks convention: caret-separated key:value
    pairs (key:value^key2:value2), OR a bare flag with no colon at all
    (e.g. "12m") -- a bare flag's presence alone is the signal, stored as
    True so a truthy check (`if tweak_values.get("12m")`) behaves the
    same way as every key:value tweak. Owned by this Base Chart
    individually, not enforced by ChartGen itself -- a de facto standard
    shared with other Base Charts where practical, but a different chart
    adopting a different structure is a legitimate design choice, not a
    deviation. Keys are lower-cased and stripped. Values are stripped of
    surrounding whitespace only ('target: 150', 'target:150' and
    'target:   150' all parse identically) -- internal casing/content of
    the value itself is preserved verbatim, since target's own value is
    echoed back literally in its on-chart label.
    """
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
    """
    Decimal places needed for `sig_figs` significant figures against a
    single reference value -- 3 sig figs by default, per this chart's own
    table convention (a whole table shares one decimal count rather than
    deciding it cell-by-cell, so its columns/rows stay aligned).
    max(0, ...) is the floor that guarantees rounding never happens above
    the unit level: a reference value of 5678 gives 0 decimals (rounds to
    5678, the nearest whole unit -- never rounds away to the nearest ten
    or hundred), rather than going negative to force a 3-sig-fig fit.
    Reference values below 1 extend decimals the other way (0.0523 -> 4
    decimals) under the same 3-sig-fig rule, since there's no unit-level
    floor to protect below zero.
    """
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
    """Apply Community Indicators submission-table styling, toned down per
    this chart's own convention: a softened header row, pale row-label
    cells, light grey borders, colour-coded value text per row. n_pad
    ("12m" tweak) hatches the first n_pad data columns' body cells (their
    "n/a" columns) to match the chart's own hatched band -- same fill as
    an ordinary body cell, with light grey hatch lines (the same colour
    as the chart's own hatch, GREYED_HATCH_COL) showing through
    underneath the "n/a" text. A Table draws as a single atomic block --
    each cell's own fill, then its own text -- regardless of the cell's
    or text's individual zorder relative to other artists, so a hatch
    added as a separate overlay patch on ax_table can only end up
    entirely above the whole table (covering the "n/a" text, an earlier
    version's mistake) or entirely below it (then hidden under the
    cell's own opaque fill) -- it can never land between the cell's fill
    and its text via zorder alone. The hatch is therefore set directly
    on the cell itself (guaranteeing it draws before that cell's own
    text, within the same atomic step), which has one side effect: a
    Cell's hatch colour and its border colour are the same underlying
    property (edgecolor), so setting the hatch also recolours the
    border. A second, border-only rectangle (transparent fill, ordinary
    LEGEND_BORDER edge, no hatch) is then drawn on top of the whole
    table to restore the correct border colour without covering the
    text -- it only paints the cell's outline, not its interior, so the
    "n/a" text and the hatch beneath it are untouched. A cell's real
    position/size isn't settled until draw time (matplotlib auto-sizes
    table columns against rendered text), so that border rectangle is
    positioned from get_window_extent() -- the same authoritative,
    post-layout bounding box matplotlib itself relies on -- converted
    from display pixels into ax_table's own data coordinates, rather
    than from the cell's own get_x/get_y/get_width/get_height/
    get_transform, which don't reliably compose for this purpose (an
    earlier version read those directly and got a rectangle collapsed
    to a few pixels, identical for every cell). Header cells for those
    columns are left alone, since the month label itself is still real
    and informative even though the data beneath it isn't."""
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
    """Line chart of one Metric-Series across every period — mean and median reference lines, a highlighted line per subsequent layer (Selected or peer group), and a per-period table of Selected/Mean/Median values beneath the chart. Chart, legend and table each occupy a fixed, non-overlapping band within a single consistent outer margin. CI report styling. "12m" tweak pads/trims onto a fixed 12-month axis, most recent months rightmost, missing early months shown as an empty hatched band."""
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
                # Falls back to unit_id, never the bare word "Selected" --
                # the unit's own identity is always shown, even when it
                # has no display code.
                selected_code = unit.unit_code or unit.unit_id
        else:
            peer_means = _to_nan_array([ps.mean for ps in layer_metric.period_stats])
            alpha = PEER_ALPHAS[peer_alpha_idx % len(PEER_ALPHAS)]
            peer_alpha_idx += 1
            peer_series.append((peer_means, layer.population_label, alpha))

    # --- Tweaks-driven target reference line: "target:XXXX" in this row's
    # own tweaks string (this chart's own tweaks convention -- see
    # _parse_tweaks). XXXX numeric -> a flat line at that value across
    # every period. XXXX the literal text "median" (case-insensitive) ->
    # tracks this metric's own median line exactly, drawn as its own
    # dashed purple line on top of, not instead of, the existing solid
    # median line. Any other/invalid value is silently ignored -- no
    # target line drawn, chart otherwise unaffected. Label always echoes
    # the tweak's own literal text (whatever case/wording the user
    # typed), with exactly one space after the colon regardless of
    # spacing in the tweak itself. ---
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

    # --- "12m" tweak: pad/trim every real per-period series onto a fixed
    # 12-month axis, most recent real month rightmost. window_size/n_pad
    # default to a no-op (window_size=n_real, n_pad=0) when the tweak
    # isn't active, so _apply_padding is always safe to call below
    # regardless of whether "12m" is set. See module docstring. ---
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
            # else: first real period's label didn't parse as "Month YYYY"
            # -- skip padding entirely for this render (n_pad stays 0)
            # rather than guessing at calendar months.

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

    # y-axis scale is computed AFTER padding/trimming, from the final
    # displayed series only -- a period trimmed off by "12m" (more than
    # 12 real months given) must not be able to inflate the axis for
    # months that are no longer even shown.
    all_values = list(means[~np.isnan(means)]) + list(medians[~np.isnan(medians)])
    if selected_y is not None:
        all_values.extend(list(selected_y[~np.isnan(selected_y)]))
    for pm, _, _ in peer_series:
        all_values.extend(list(pm[~np.isnan(pm)]))
    if target_series is not None:
        all_values.extend(list(target_series[~np.isnan(target_series)]))

    max_plotted = max(all_values) if all_values else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)

    # Whole visualisation (chart + legend + table) is sized to width_emu/
    # height_emu - no extra scaling beyond that.
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

    # --- "12m" tweak: hatched band over the synthetic no-data months,
    # plus a dashed divider marking exactly where real data begins.
    # facecolor "none" (transparent) so the ordinary gridlines still show
    # through between the hatch strokes -- this reads as "switched off",
    # not "broken" or "an error". zorder sits just above the gridlines
    # (0) but below the baseline (1) and every plotted line (2+), so the
    # hatch never draws over real content. ---
    if n_pad:
        ax.axvspan(-0.5, n_pad - 0.5, facecolor="none", edgecolor=GREYED_HATCH_COL,
                   hatch="///", linewidth=0, zorder=0.5)
        ax.axvline(n_pad - 0.5, color=GREYED_DIVIDER_COL, linewidth=1 * TEXT_SCALE,
                   linestyle=(0, (4 * TEXT_SCALE, 3 * TEXT_SCALE)), zorder=0.6)

    handles = []
    legend_labels = []

    # Draw order: median, mean, peer groups, selected organisation on top.
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
        # Labelled via the legend (last entry, added after the reversal
        # below) rather than an on-chart label -- an on-chart label's
        # position can't be guaranteed clear of other chart content
        # (data points, other lines, the plot's own edges), whereas the
        # legend is a fixed, reserved band the label can never clash with.

    # Month labels appear once only, as the table's header row below - the
    # chart's own x-axis is left unlabelled to avoid repeating them.
    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_xlim(-0.5, n_periods - 0.5)
    _apply_axes_style(ax, y_max, y_step)
    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier, 0))

    # Legend occupies its own fixed figure-coordinate band between the
    # chart and the table (positioned in absolute figure space, not
    # relative to the chart axes, so it cannot bleed into either
    # neighbouring band regardless of legend content length).
    reversed_handles = list(reversed(handles))
    reversed_labels = list(reversed(legend_labels))
    # Target is appended after the reversal, not folded into `handles`
    # beforehand, so it always lands as the legend's last (rightmost)
    # entry regardless of how many other series are present -- reversing
    # a list that already ended with target would instead put it first.
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

    # --- Per-period table: header row of month labels, then Selected,
    # Mean, Median rows, aligned with the chart's plot area above. Decimal
    # places are decided once for the whole table (not per cell, since a
    # table with different decimal counts per row/column wouldn't align)
    # -- driven by the mean of this table's own values (Selected, Mean,
    # Median together, NaNs excluded), via _sig_fig_decimals. Applies
    # equally regardless of format_modifier (P/C included), per this
    # chart's own table convention. "12m" tweak: the first n_pad columns
    # get the literal text "n/a" in every row instead of the ordinary
    # "-" no-data marker, and are greyed/hatched by _style_table -- there
    # is by definition no real value to show for a synthetic month, so
    # this is distinguished from an ordinary missing value within real
    # data. ---
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
    # "12m" tweak: a table's real cell positions/sizes aren't finalised
    # until the figure is actually drawn (matplotlib auto-sizes columns
    # against rendered text at draw time) -- reading cell geometry any
    # earlier returns stale placeholder values, which is what was
    # producing a near-zero-size hatch overlay identical for every cell.
    # Forcing a draw pass here resolves real column widths/positions
    # first, so _style_table's hatch overlay reads genuine cell bounds.
    fig.canvas.draw()
    _style_table(table, selected_y is not None, n_pad, ax_table)

    return _fig_to_bytes(fig)
