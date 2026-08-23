"""Base Chart, NumericSeries. Ranked descending column chart, Selected organisation highlighted, median reference line. CI report styling. Units with no data are excluded entirely rather than plotted as zero."""

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
import matplotlib.transforms as mtransforms


SELECTED_RED  = "#DA291C"
OTHER_BLUE    = "#005EB8"
MEDIAN_GREEN  = "#78BE20"
AXIS_GREY     = "#5B6770"
GRID_GREY     = "#DFE6EE"
BASELINE_GREY = "#2F3A45"
CARD_BG       = "#F0F5FC"
LEGEND_BORDER = "#E6E9ED"
TARGET_PURPLE = "#9B30FF"

EMU_PER_INCH = 914400

TEXT_SCALE = 5


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


PLOT_BG = _tint(CARD_BG, 0.25)

MARGIN        = 0.055
LABEL_GUTTER  = 0.048
LEGEND_HEIGHT = 0.085
BUFFER        = 0.055

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
    """This chart's own tweaks grammar: caret-separated key:value pairs. One key is read, target:N or target:median, drawing a reference line at that value."""
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
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(PLOT_BG)
    ax.text(0.5, 0.5, "No data", ha="center", va="center", color=AXIS_GREY, fontsize=10 * TEXT_SCALE)
    ax.axis("off")
    return _fig_to_bytes(fig)


def column_ci_full(population_layers: list, width_emu=5486400, height_emu=3429000, tweaks=""):
    base = population_layers[0]
    ms = base.metric_stats[0]

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

    sel_unit_id, sel_code, sel_val = _selected_identity(population_layers)
    sel_idx = next((i for i, u in enumerate(units) if u.unit_id == sel_unit_id), None) \
        if sel_unit_id is not None else None

    key_values = [v for v in (sel_val, ms.mean, ms.median) if v is not None]
    key_mean = float(np.mean(np.abs(key_values))) if key_values else 0.0
    key_decimals = _sig_fig_decimals(key_mean)

    colours = [SELECTED_RED if i == sel_idx else OTHER_BLUE for i in range(len(units))]

    slot_width = 0.6
    ax.bar(x, values, color=colours, width=slot_width, zorder=2)

    if sel_idx is not None and sel_val is not None:
        ax.annotate(_format_number(sel_val, base.format_modifier, decimals=key_decimals),
                    xy=(sel_idx, sel_val), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=8 * TEXT_SCALE, color=SELECTED_RED, fontweight="bold",
                    zorder=10,
                    bbox=dict(facecolor="white", alpha=0.6, edgecolor="none", boxstyle="square,pad=0.2"))

    if ms.median is not None: ax.axhline(ms.median, color=MEDIAN_GREEN, linewidth=2 * TEXT_SCALE, zorder=3)

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

    candidates = [v for v in values if v is not None]
    if ms.median is not None: candidates.append(ms.median)
    if target_value is not None: candidates.append(target_value)
    max_plotted = max(candidates) if candidates else 1.0
    y_max, y_step = _nice_axis_bounds(max_plotted)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(y_step))

    if target_value is not None:
        ax.axhline(target_value, color=TARGET_PURPLE, linewidth=2 * TEXT_SCALE, linestyle="--", zorder=4)
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

    mean_label   = f"Mean: {_format_number(ms.mean, base.format_modifier, decimals=key_decimals)}" if ms.mean is not None else "Mean: -"
    median_label = f"Median: {_format_number(ms.median, base.format_modifier, decimals=key_decimals)}" if ms.median is not None else "Median: -"
    sel_value_text = _format_number(sel_val, base.format_modifier, decimals=key_decimals) if sel_val is not None else "n/a"
    handles = [
        plt.matplotlib.patches.Patch(color=SELECTED_RED, label=f"{sel_code or 'Selected'}: {sel_value_text}"),
        plt.matplotlib.patches.Patch(color=OTHER_BLUE, label="Other providers"),
        plt.Line2D([0], [0], color=MEDIAN_GREEN, linewidth=2 * TEXT_SCALE, label=median_label),
        plt.Line2D([0], [0], color="none", label=mean_label),
    ]
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
