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
"""

import io
import math
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font, baked into the SVG
# vector output as real glyph outlines (svg.fonttype default "path").
# See Architecture, SVG rendering methodology (Decision 27). The source
# bundle used Arial (the CI report spec's own typography) — kept as
# Calibri here per that governed decision, same as column_ci_full.
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SELECTED_COL   = "#DA291C"   # NHS Red - this organisation
MEAN_COL       = "#009639"   # NHS Green (dark) - mean
MEDIAN_COL     = "#78BE20"   # NHS Light Green - median
OTHER_COL      = "#005EB8"   # NHS Blue - peer groups
GRID_COL       = "#DFE6EE"   # pale grey - gridlines
BASELINE_COL   = "#2F3A45"   # dark grey - baseline
AXIS_LABEL_COL = "#5B6770"   # grey - axis tick labels
CARD_BG        = "#F0F5FC"   # outer card background (figure)
LEGEND_BORDER  = "#E6E9ED"   # light grey - legend / table border

PEER_ALPHAS = [1.0, 0.7, 0.5, 0.35]

VALUE_DECIMAL_PLACES = 2

EMU_PER_INCH = 914400

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


PLOT_BG        = _tint(CARD_BG, 0.25)    # plot area background, 25% of current strength
TABLE_CELL_BG  = _tint(CARD_BG, 0.25)    # table body cell background, matching the plot area
HEADER_BG      = _tint(OTHER_COL, 0.35)  # table header row, deliberately toned down
ROWLABEL_BG    = _tint("#EFF5FC", 0.6)   # table row-label background, kept a little more visible


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


def _format_value(value, format_modifier, decimals=VALUE_DECIMAL_PLACES):
    """Standard Base Chart formatting rule: "P" appends "%", "C" prefixes
    "£", anything else (including "N", or blank) gets plain comma-thousands
    formatting with no suffix at all."""
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


def _apply_axes_style(ax, y_max, step):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(step))
    ax.yaxis.grid(True, color=GRID_COL, linewidth=0.5, zorder=0)
    ax.xaxis.grid(False)
    ax.axhline(0, color=BASELINE_COL, linewidth=0.8, zorder=1)
    ax.tick_params(axis="y", labelsize=7, colors=AXIS_LABEL_COL, length=0)
    ax.tick_params(axis="x", length=0)


def _empty_chart(width_emu, height_emu):
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)
    ax.text(0.5, 0.5, "No data", ha="center", va="center")
    ax.axis("off")
    return _fig_to_bytes(fig)


def _style_table(table, has_selected_row):
    """Apply Community Indicators submission-table styling, toned down per
    this chart's own convention: a softened header row, pale row-label
    cells, light grey borders, colour-coded value text per row."""
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)

    row_colours = []
    if has_selected_row:
        row_colours.append(SELECTED_COL)
    row_colours.append(MEAN_COL)
    row_colours.append(MEDIAN_COL)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(LEGEND_BORDER)
        cell.set_linewidth(0.8)
        if row == 0:
            cell.set_facecolor(HEADER_BG)
            cell.set_text_props(color=BASELINE_COL, fontweight="bold", fontsize=7)
        elif col == -1:
            cell.set_facecolor(ROWLABEL_BG)
            cell.set_text_props(fontweight="bold", fontsize=7,
                                 color=row_colours[row - 1])
        else:
            cell.set_facecolor(TABLE_CELL_BG)
            cell.set_text_props(color=AXIS_LABEL_COL, fontsize=7)


def line_ci_full(population_layers: list, width_emu=5486400, height_emu=3086100, tweaks=""):
    """Line chart of one Metric-Series across every period — mean and median reference lines, a highlighted line per subsequent layer (Selected or peer group), and a per-period table of Selected/Mean/Median values beneath the chart. Chart, legend and table each occupy a fixed, non-overlapping band within a single consistent outer margin. CI report styling."""
    if not population_layers:
        return _empty_chart(width_emu, height_emu)

    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not base.periods:
        return _empty_chart(width_emu, height_emu)

    month_labels = [_month_label(p.period_label) for p in base.periods]
    n_periods = len(base.periods)
    x = np.arange(n_periods)

    medians = _to_nan_array([ps.median for ps in metric.period_stats])
    means = _to_nan_array([ps.mean for ps in metric.period_stats])

    all_values = list(means[~np.isnan(means)]) + list(medians[~np.isnan(medians)])

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
                all_values.extend(list(selected_y[~np.isnan(selected_y)]))
        else:
            peer_means = _to_nan_array([ps.mean for ps in layer_metric.period_stats])
            alpha = PEER_ALPHAS[peer_alpha_idx % len(PEER_ALPHAS)]
            peer_alpha_idx += 1
            peer_series.append((peer_means, layer.population_label, alpha))
            all_values.extend(list(peer_means[~np.isnan(peer_means)]))

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

    handles = []
    legend_labels = []

    # Draw order: median, mean, peer groups, selected organisation on top.
    line, = ax.plot(x, medians, color=MEDIAN_COL, linewidth=1.8, zorder=2)
    handles.append(line)
    legend_labels.append("Median")

    line, = ax.plot(x, means, color=MEAN_COL, linewidth=1.8, zorder=3)
    handles.append(line)
    legend_labels.append("Mean")

    for peer_means, peer_label, alpha in peer_series:
        line, = ax.plot(x, peer_means, color=OTHER_COL, linewidth=1.5,
                         linestyle="--", alpha=alpha, zorder=4)
        handles.append(line)
        legend_labels.append(peer_label)

    if selected_y is not None:
        line, = ax.plot(x, selected_y, color=SELECTED_COL, linewidth=2.2,
                         marker="o", markersize=4, markerfacecolor=SELECTED_COL,
                         markeredgecolor=SELECTED_COL, zorder=5)
        handles.append(line)
        legend_labels.append(f"{selected_code} (this organisation)")

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
    legend = fig.legend(
        reversed_handles, reversed_labels,
        loc="lower left",
        bbox_to_anchor=(_content_left, legend_bottom, _content_width, LEGEND_HEIGHT),
        bbox_transform=fig.transFigure,
        mode="expand",
        ncol=len(reversed_handles),
        fontsize=9,
        frameon=True,
        borderaxespad=0,
        labelcolor=AXIS_LABEL_COL,
    )
    legend.get_frame().set_facecolor(CARD_BG)
    legend.get_frame().set_edgecolor(LEGEND_BORDER)
    legend.get_frame().set_linewidth(0.8)

    # --- Per-period table: header row of month labels, then Selected,
    # Mean, Median rows, aligned with the chart's plot area above. ---
    row_labels = []
    cell_text = []
    if selected_y is not None:
        row_labels.append(selected_code or "Selected")
        cell_text.append([_format_value(v, base.format_modifier) for v in selected_y])
    row_labels.append("Mean")
    cell_text.append([_format_value(v, base.format_modifier) for v in means])
    row_labels.append("Median")
    cell_text.append([_format_value(v, base.format_modifier) for v in medians])

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
    _style_table(table, selected_y is not None)

    return _fig_to_bytes(fig)
