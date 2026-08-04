"""
column_ci_full.py
Base Chart — NumericSeries. Ranked descending column chart, restyled to
the Community Indicators (CI) report's colour/typography/layout
specification. Logic is unchanged from `ranked_column` (population layer
handling, Selected identification, mean/median reading) — only the visual
formatting (colours, reference lines shown, legend, sizing, labelling)
follows the CI spec.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) — no report_context or any other runtime object. The
Selected unit's identity comes from the "Selected"-labelled entry in
population_layers, the same convention every other Base Chart uses.

Note: font kept as Calibri per Architecture Decision 27 (governs every
Base Chart), not Arial as given in the CI spec's own typography section —
flagged for confirmation rather than silently overridden.

Card background, plot-area tint, and the bordered legend card all match
`line_ci_full`'s own palette treatment as closely as possible, so the two
CI-styled charts read as one consistent family rather than two
independently-styled charts that happen to share a colour palette. The
legend now also matches `line_ci_full`'s own figure layout exactly: a
fixed chart band and a fixed legend band, both anchored to the same
left/right figure-fraction coordinates, so the legend sits directly under
the plot area in exact alignment, as a single row (fig.legend with
mode="expand"), rather than an axes-relative legend that happens to be
roughly underneath.

The Selected organisation's own identity is always its unit code, falling
back to its unit id if no code exists — never the bare word "Selected".
Its value is shown alongside its legend entry; "n/a" if this metric has
no value for it (which can happen independently of whether it appears as
a bar — a unit with no data is excluded from the bars entirely, but still
gets a legend entry, since it's still "this organisation" even without a
value to plot).
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
# See Architecture, SVG rendering methodology (Decision 27).
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# CI report palette — inlined, this chart's own copy
# ---------------------------------------------------------------------------

SELECTED_RED  = "#DA291C"   # NHS Red — selected organisation
OTHER_BLUE    = "#005EB8"   # NHS Blue — every other organisation, one shade
MEAN_GREEN    = "#009639"   # NHS Green (dark) — mean reference line
MEDIAN_GREEN  = "#78BE20"   # NHS Light Green — median reference line
AXIS_GREY     = "#5B6770"   # axis / tick labels
GRID_GREY     = "#DFE6EE"   # gridlines
BASELINE_GREY = "#2F3A45"   # x-axis baseline
CARD_BG       = "#F0F5FC"   # outer card background (figure) — matches line_ci_full
LEGEND_BORDER = "#E6E9ED"   # light grey — legend card border, matches line_ci_full

EMU_PER_INCH = 914400


def _hex_to_rgb(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    return tuple(int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def _tint(hex_colour, strength):
    """Blend a colour toward white. strength=1.0 keeps the colour as-is;
    strength=0.25 keeps only a quarter of its distance from white (i.e.
    a much paler version of the same colour). Matches line_ci_full's own
    copy of this helper exactly."""
    r, g, b = _hex_to_rgb(hex_colour)
    r = 255 - (255 - r) * strength
    g = 255 - (255 - g) * strength
    b = 255 - (255 - b) * strength
    return _rgb_to_hex((r, g, b))


PLOT_BG = _tint(CARD_BG, 0.25)   # plot area background, matches line_ci_full's own plot tint

# --- Figure layout: fixed chart band and legend band, both anchored to
# the same left/right figure-fraction coordinates -- matches line_ci_full's
# own layout approach exactly, so the legend sits directly under the plot
# area in exact alignment rather than an axes-relative legend that's only
# roughly underneath. LABEL_GUTTER reserves room, ahead of the axes' left
# edge, for the y-axis tick labels, which matplotlib draws outside the
# axes' own bounding box. ---
MARGIN        = 0.055   # identical on top, bottom, left and right
LABEL_GUTTER  = 0.048   # reserved for y-axis tick labels
LEGEND_HEIGHT = 0.085
BUFFER        = 0.020   # between legend and chart plot area

_content_left   = MARGIN + LABEL_GUTTER
_content_width  = 1.0 - (2 * MARGIN) - LABEL_GUTTER
_content_bottom = MARGIN
_content_top    = 1.0 - MARGIN


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _apply_spine_style(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.axhline(0, color=BASELINE_GREY, linewidth=0.8, zorder=1)
    ax.set_axisbelow(True)


def _format_number(value, format_modifier, decimals=0):
    if value is None:
        return "-"
    if format_modifier == "P":
        return f"{value:,.{decimals}f}%"
    if format_modifier == "C":
        return f"£{value:,.{decimals}f}"
    return f"{value:,.{decimals}f}"


def _axis_formatter(format_modifier):
    return mticker.FuncFormatter(lambda v, _: _format_number(v, format_modifier))


def _nice_number(value, round_to_nearest=False):
    """Nice-numbers axis algorithm (Heckbert-style): returns a rounded
    figure close to `value` using only 1/2/3/4/5-times-a-power-of-ten
    steps (a wider set than the classic 1/2/5 — agreed to give a snugger
    fit against real data, e.g. a step of 300 rather than jumping straight
    to 500). Matches line_ci_full's own copy of this helper exactly."""
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
    with a matching 'nice' tick step -- 10% top padding, step derived
    directly from padded-max/target-bands rather than a coarse pre-rounded
    range, so the axis stays snug to the data instead of occasionally
    overshooting to the next tier. Band count is a target, not a
    guarantee. Matches line_ci_full's own axis logic exactly."""
    if max_plotted_value <= 0:
        return 1.0, 0.2
    padded = max_plotted_value * 1.10
    raw_step = padded / target_ticks
    step = _nice_number(raw_step, round_to_nearest=True)
    y_max = math.ceil(padded / step) * step
    return y_max, step


def _selected_identity(population_layers):
    """
    The Selected unit's own identity and value, read directly from the
    "Selected"-labelled population layer — independent of whether that
    unit has data for this metric (and so appears among the plotted
    bars, which exclude no-data units entirely). Code falls back to
    unit_id if no display code exists, never the bare word "Selected".
    Where more than one unit is Selected, the first is used as the
    representative. Returns (unit_id, code, value) or (None, None, None).
    """
    selected_layer = next((l for l in population_layers if l.population_label == "Selected"), None)
    if selected_layer is None or not selected_layer.units:
        return None, None, None
    unit = selected_layer.units[0]
    code = unit.unit_code or unit.unit_id
    return unit.unit_id, code, unit.values[0]


def _empty_chart(width_emu, height_emu):
    w, h = _size_to_inches(width_emu, height_emu)
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(PLOT_BG)
    ax.text(0.5, 0.5, "No data", ha="center", va="center", color=AXIS_GREY)
    ax.axis("off")
    return _fig_to_bytes(fig)


def column_ci_full(population_layers: list, width_emu=5486400, height_emu=3429000, tweaks=""):
    """Ranked descending column chart — Selected organisation highlighted, mean/median reference lines. CI report styling. Units with no data for this metric are excluded entirely (not plotted as zero), so the remaining bars widen to fill the space rather than leaving empty slots."""
    base = population_layers[0]
    ms = base.metric_stats[0]

    # Units with no value are excluded outright, not plotted as a
    # zero-height bar in a reserved slot — the remaining bars widen
    # automatically to fill the space this frees up, since x-positions are
    # assigned only across units that actually have data.
    units = sorted(
        (u for u in base.units if u.values[0] is not None),
        key=lambda u: -u.values[0],
    )
    if not units:
        return _empty_chart(width_emu, height_emu)

    w, h = _size_to_inches(width_emu, height_emu)
    fig = plt.figure(figsize=(w, h))
    fig.patch.set_facecolor(CARD_BG)

    legend_bottom = _content_bottom
    chart_bottom  = legend_bottom + LEGEND_HEIGHT + BUFFER
    chart_height  = _content_top - chart_bottom

    ax = fig.add_axes([_content_left, chart_bottom, _content_width, chart_height])
    ax.set_facecolor(PLOT_BG)
    codes  = [u.unit_code for u in units]
    values = [u.values[0] for u in units]
    x = np.arange(len(codes))

    # Selected identity/value come directly from the Selected layer, not
    # from a lookup within `units` (which excludes no-data units) -- so
    # the legend always has something to show for "this organisation"
    # even when it has no bar. sel_idx (used only for bar highlighting/
    # on-chart annotation) is a separate, possibly-None lookup against
    # the units actually plotted.
    sel_unit_id, sel_code, sel_val = _selected_identity(population_layers)
    sel_idx = next((i for i, u in enumerate(units) if u.unit_id == sel_unit_id), None) \
        if sel_unit_id is not None else None

    # Binary colouring only — Selected vs everyone else, per CI spec
    # (no distinct peer-group colour; a peer token still narrows the
    # scope upstream, same as every other Base Chart, it just isn't
    # given its own colour here).
    colours = [SELECTED_RED if i == sel_idx else OTHER_BLUE for i in range(len(units))]

    slot_width = 0.6  # bar occupies middle 60% of its slot, per CI spec
    ax.bar(x, values, color=colours, width=slot_width, zorder=2)

    if sel_idx is not None and sel_val is not None:
        ax.annotate(_format_number(sel_val, base.format_modifier, decimals=1),
                    xy=(sel_idx, sel_val), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=8, color=SELECTED_RED, fontweight="bold")

    # Reference lines: mean/median only — no quartiles, per CI spec
    if ms.mean   is not None: ax.axhline(ms.mean,   color=MEAN_GREEN,   linewidth=2, zorder=3)
    if ms.median is not None: ax.axhline(ms.median, color=MEDIAN_GREEN, linewidth=2, zorder=3)

    # Y scale — nice-numbers algorithm (Heckbert), 10% top padding, 5 bands
    # / 6 gridlines including top and bottom — matches line_ci_full's own
    # axis logic exactly, replacing the old LinearLocator(5) (which just
    # divided an arbitrary padded max into 5 equal, non-round steps).
    candidates = [v for v in values if v is not None]
    if ms.mean   is not None: candidates.append(ms.mean)
    if ms.median is not None: candidates.append(ms.median)
    max_plotted = max(candidates) if candidates else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(y_step))

    ax.set_xticks(x)
    tick_labels = ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=6.5)
    for i, lbl in enumerate(tick_labels):
        if i == sel_idx:
            lbl.set_color(SELECTED_RED)
            lbl.set_fontweight("bold")
        else:
            lbl.set_color(AXIS_GREY)

    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=7, colors=AXIS_GREY)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.grid(True, color=GRID_GREY, linewidth=0.5)
    _apply_spine_style(ax)

    mean_label   = f"Mean: {_format_number(ms.mean, base.format_modifier, decimals=1)}" if ms.mean is not None else "Mean: -"
    median_label = f"Median: {_format_number(ms.median, base.format_modifier, decimals=1)}" if ms.median is not None else "Median: -"
    sel_value_text = _format_number(sel_val, base.format_modifier, decimals=1) if sel_val is not None else "n/a"
    handles = [
        plt.matplotlib.patches.Patch(color=SELECTED_RED, label=f"{sel_code or 'Selected'} (this organisation): {sel_value_text}"),
        plt.matplotlib.patches.Patch(color=OTHER_BLUE, label="Other providers"),
        plt.Line2D([0], [0], color=MEAN_GREEN,   linewidth=2, label=mean_label),
        plt.Line2D([0], [0], color=MEDIAN_GREEN, linewidth=2, label=median_label),
    ]
    # Figure-anchored, not axes-relative -- bbox spans exactly the same
    # left/right coordinates the axes itself sits at (_content_left/
    # _content_width), so the legend sits directly under the plot area in
    # exact alignment. mode="expand" plus ncol=len(handles) forces a
    # single row spanning that full width, matching line_ci_full's own
    # legend treatment exactly.
    legend = fig.legend(
        handles, [h.get_label() for h in handles],
        loc="lower left",
        bbox_to_anchor=(_content_left, legend_bottom, _content_width, LEGEND_HEIGHT),
        bbox_transform=fig.transFigure,
        mode="expand",
        ncol=len(handles),
        fontsize=9,
        frameon=True,
        borderaxespad=0,
        labelcolor=AXIS_GREY,
    )
    legend.get_frame().set_facecolor(CARD_BG)
    legend.get_frame().set_edgecolor(LEGEND_BORDER)
    legend.get_frame().set_linewidth(0.8)
    return _fig_to_bytes(fig)
