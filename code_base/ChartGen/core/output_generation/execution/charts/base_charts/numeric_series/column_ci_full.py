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

# Calibri -- ChartGen's standard chart/table font (Decision 27, governs
# every Base Chart), not Arial as given in the CI spec's own typography
# section -- flagged for confirmation rather than silently overridden.
# SVG text is kept as real text, not glyph outlines -- see line_ci_full's
# own comment for the full reasoning.
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms

# ---------------------------------------------------------------------------
# CI report palette — inlined, this chart's own copy
# ---------------------------------------------------------------------------

SELECTED_RED  = "#DA291C"   # NHS Red — selected organisation
OTHER_BLUE    = "#005EB8"   # NHS Blue — every other organisation, one shade
MEDIAN_GREEN  = "#78BE20"   # NHS Light Green — median reference line
AXIS_GREY     = "#5B6770"   # axis / tick labels
GRID_GREY     = "#DFE6EE"   # gridlines
BASELINE_GREY = "#2F3A45"   # x-axis baseline
CARD_BG       = "#F0F5FC"   # outer card background (figure) — matches line_ci_full
LEGEND_BORDER = "#E6E9ED"   # light grey — legend card border, matches line_ci_full
TARGET_PURPLE = "#9B30FF"   # bright purple — tweaks-driven target reference line, this chart's own copy (matches line_ci_full's)

EMU_PER_INCH = 914400

# PowerPoint SVG-text-compression workaround -- see line_ci_full's own
# TEXT_SCALE comment for the full reasoning. Must match the system
# layer's own CHART_RENDER_SCALE (assembly_engine.py) exactly.
TEXT_SCALE = 5


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
BUFFER        = 0.055   # between legend and chart plot area -- also the only
                         # space reserved for the x-axis unit-code tick labels,
                         # which matplotlib draws below the axes' own bounding
                         # box; widened from 0.020 (was tight enough that the
                         # tick labels overlapped the legend directly below)

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
    ax.axhline(0, color=BASELINE_GREY, linewidth=0.8 * TEXT_SCALE, zorder=1)
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


def _parse_tweaks(tweaks: str) -> dict:
    """
    Parse this chart's own tweaks convention: caret-separated key:value
    pairs (key:value^key2:value2). Owned by this Base Chart individually,
    not enforced by ChartGen itself -- a de facto standard shared with
    other Base Charts where practical, but a different chart adopting a
    different structure is a legitimate design choice, not a deviation.
    Keys are lower-cased and stripped. Values are stripped of surrounding
    whitespace only ('target: 150', 'target:150' and 'target:   150' all
    parse identically) -- internal casing/content of the value itself is
    preserved verbatim, since target's own value is echoed back literally
    in its on-chart label.
    """
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
    """
    Decimal places needed for `sig_figs` significant figures against a
    single reference value -- 3 sig figs by default, per this chart's own
    key convention (the legend's three numeric values -- Selected, Mean,
    Median -- share one decimal count rather than deciding it value-by-
    value, so they read consistently alongside each other). max(0, ...)
    is the floor that guarantees rounding never happens above the unit
    level: a reference value of 5678 gives 0 decimals (rounds to 5678,
    the nearest whole unit -- never rounds away to the nearest ten or
    hundred), rather than going negative to force a 3-sig-fig fit.
    Reference values below 1 extend decimals the other way (0.0523 -> 4
    decimals) under the same 3-sig-fig rule, since there's no unit-level
    floor to protect below zero. Own copy, matches line_ci_full's exactly.
    """
    if reference_value is None:
        return 0
    reference_value = abs(reference_value)
    if reference_value == 0 or math.isnan(reference_value):
        return 0
    return max(0, (sig_figs - 1) - math.floor(math.log10(reference_value)))


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
    ax.text(0.5, 0.5, "No data", ha="center", va="center", color=AXIS_GREY, fontsize=10 * TEXT_SCALE)
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

    # --- Key (legend) decimal places: one shared count for all three
    # numeric values shown in the key (Selected, Mean, Median), driven by
    # their mean magnitude (not the "Mean" reference line specifically --
    # the statistical mean of whichever of the three values are present),
    # via _sig_fig_decimals -- same convention as line_ci_full's own
    # table. NaN-safe: a missing value is simply left out of the mean
    # calculation, same as it's already left out of its own legend entry
    # ("Mean: -" etc). Computed here (rather than down by the legend
    # itself) so the bar-top annotation below can share it too -- the
    # Selected value appears in both places and must read identically in
    # both, not just independently "correct" in each. ---
    key_values = [v for v in (sel_val, ms.mean, ms.median) if v is not None]
    key_mean = float(np.mean(np.abs(key_values))) if key_values else 0.0
    key_decimals = _sig_fig_decimals(key_mean)

    # Binary colouring only — Selected vs everyone else, per CI spec
    # (no distinct peer-group colour; a peer token still narrows the
    # scope upstream, same as every other Base Chart, it just isn't
    # given its own colour here).
    colours = [SELECTED_RED if i == sel_idx else OTHER_BLUE for i in range(len(units))]

    slot_width = 0.6  # bar occupies middle 60% of its slot, per CI spec
    ax.bar(x, values, color=colours, width=slot_width, zorder=2)

    if sel_idx is not None and sel_val is not None:
        ax.annotate(_format_number(sel_val, base.format_modifier, decimals=key_decimals),
                    xy=(sel_idx, sel_val), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=8 * TEXT_SCALE, color=SELECTED_RED, fontweight="bold",
                    zorder=10,
                    bbox=dict(facecolor="white", alpha=0.6, edgecolor="none", boxstyle="square,pad=0.2"))

    # Reference lines: median only -- mean is no longer drawn on-chart
    # (still shown as a text-only legend entry, after Median, with no
    # colour swatch -- see handles below), per this chart's own display
    # convention.
    if ms.median is not None: ax.axhline(ms.median, color=MEDIAN_GREEN, linewidth=2 * TEXT_SCALE, zorder=3)

    # --- Tweaks-driven target reference line: "target:XXXX" in this row's
    # own tweaks string (this chart's own tweaks convention -- see
    # _parse_tweaks). XXXX numeric -> a flat line at that value. XXXX the
    # literal text "median" (case-insensitive) -> tracks this metric's own
    # median value exactly (drawn as its own dashed purple line on top of,
    # not instead of, the existing solid median line). Any other/invalid
    # value is silently ignored -- no target line drawn, chart otherwise
    # unaffected. Label always echoes the tweak's own literal text
    # (whatever case/wording the user typed), with exactly one space
    # after the colon regardless of spacing in the tweak itself. ---
    tweak_values = _parse_tweaks(tweaks)
    target_raw = tweak_values.get("target")
    target_value = None
    if target_raw:
        if target_raw.lower() == "median":
            target_value = ms.median
        else:
            try:
                target_value = float(target_raw)
            except ValueError:
                target_value = None

    # Y scale — nice-numbers algorithm (Heckbert), 10% top padding, 5 bands
    # / 6 gridlines including top and bottom — matches line_ci_full's own
    # axis logic exactly, replacing the old LinearLocator(5) (which just
    # divided an arbitrary padded max into 5 equal, non-round steps).
    candidates = [v for v in values if v is not None]
    if ms.median is not None: candidates.append(ms.median)
    if target_value is not None: candidates.append(target_value)
    max_plotted = max(candidates) if candidates else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(y_step))

    if target_value is not None:
        ax.axhline(target_value, color=TARGET_PURPLE, linewidth=2 * TEXT_SCALE, linestyle="--", zorder=4)
        # Right edge of the plot area, above the line -- x anchored to the
        # axes' own right edge (axes-fraction), y anchored to the target's
        # own data value (blended transform), so the label sits exactly
        # above the target line regardless of where that value falls.
        label_trans = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
        ax.text(1.0, target_value, f"Target: {target_raw}",
                transform=label_trans, ha="right", va="bottom",
                fontsize=8 * TEXT_SCALE, color=TARGET_PURPLE, fontweight="bold",
                bbox=dict(facecolor="white", alpha=0.6, edgecolor="none", boxstyle="square,pad=0.2"))

    ax.set_xticks(x)
    tick_labels = ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=6.5 * TEXT_SCALE)
    for i, lbl in enumerate(tick_labels):
        if i == sel_idx:
            lbl.set_color(SELECTED_RED)
            lbl.set_fontweight("bold")
        else:
            lbl.set_color(AXIS_GREY)

    ax.yaxis.set_major_formatter(_axis_formatter(base.format_modifier))
    ax.tick_params(axis="y", labelsize=7 * TEXT_SCALE, colors=AXIS_GREY)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.grid(True, color=GRID_GREY, linewidth=0.5 * TEXT_SCALE)
    _apply_spine_style(ax)

    # --- Key (legend) labels, using key_decimals computed above ---
    mean_label   = f"Mean: {_format_number(ms.mean, base.format_modifier, decimals=key_decimals)}" if ms.mean is not None else "Mean: -"
    median_label = f"Median: {_format_number(ms.median, base.format_modifier, decimals=key_decimals)}" if ms.median is not None else "Median: -"
    sel_value_text = _format_number(sel_val, base.format_modifier, decimals=key_decimals) if sel_val is not None else "n/a"
    handles = [
        plt.matplotlib.patches.Patch(color=SELECTED_RED, label=f"{sel_code or 'Selected'}: {sel_value_text}"),
        plt.matplotlib.patches.Patch(color=OTHER_BLUE, label="Other providers"),
        plt.Line2D([0], [0], color=MEDIAN_GREEN, linewidth=2 * TEXT_SCALE, label=median_label),
        # Mean is text-only in the legend -- no colour swatch, since it's
        # no longer drawn as a line on the chart itself (see reference
        # lines above). An invisible handle (colour "none") still gives
        # the legend a slot to put the label text in, without a coloured
        # marker suggesting a visible chart element that isn't there.
        plt.Line2D([0], [0], color="none", label=mean_label),
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
        fontsize=9 * TEXT_SCALE,
        frameon=True,
        borderaxespad=0,
        labelcolor=AXIS_GREY,
    )
    legend.get_frame().set_facecolor(CARD_BG)
    legend.get_frame().set_edgecolor(LEGEND_BORDER)
    legend.get_frame().set_linewidth(0.8 * TEXT_SCALE)
    return _fig_to_bytes(fig)
