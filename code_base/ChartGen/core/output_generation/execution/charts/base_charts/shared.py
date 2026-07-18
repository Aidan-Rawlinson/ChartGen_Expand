"""
shared.py
Shared palette, sizing constants, and rendering helpers used across all
Base Chart functions, regardless of data shape.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

BAR_BLUE     = "#7CB9E8"
MEAN_COL     = "#E87722"
MEDIAN_COL   = "#4CAF50"
QUARTILE_COL = "#888888"
YES_COL      = "#4CAF50"
NO_COL       = "#C0392B"
NAVY         = "#1F4E79"
ORANGE       = "#E87722"
HIGHLIGHT    = "#C12958"   # TBN crimson — Selected population
GREY_LIGHT   = "#D9D9D9"   # background spaghetti lines — full/largest population, de-emphasised
PIE_COLOURS  = ["#1F4E79", "#E87722", "#7030A0", "#2E86AB", "#F0A500", "#4CAF50"]
PEER_COLOURS = ["#2E9E75", "#7030A0", "#E87722", "#2E86AB"]  # one per peer group layer

DPI = 300
NARROWER_DIM_INCHES = 7.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _size_to_inches(width, height):
    s = NARROWER_DIM_INCHES / 100
    return width * s, height * s


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _apply_spine_style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


def _format_number(value, format_modifier):
    """
    Format a scalar value per the shape's format_modifier, Excel-style:
    no modifier -> comma-thousands, no decimals ("#,###"); "P" -> the same
    plus a "%" suffix ("#,##0%"); "C" -> the same with a "£" prefix
    ("£#,##0"). Values are not rescaled (a "P" value is assumed already on
    a 0-100-ish percentage scale, per the API's own convention) — this only
    controls display. Returns "" for None.
    """
    if value is None:
        return ""
    if format_modifier == "P":
        return f"{value:,.0f}%"
    if format_modifier == "C":
        return f"£{value:,.0f}"
    return f"{value:,.0f}"


def _axis_formatter(format_modifier):
    """Matplotlib tick formatter applying _format_number for the given format_modifier."""
    return mticker.FuncFormatter(lambda v, _: _format_number(v, format_modifier))


def _resolve_unit_colours(units: list, population_layers: list) -> list:
    """Assign a colour to each unit based on which population layer(s) it belongs to."""
    colours = [BAR_BLUE] * len(units)
    peer_colour_idx = 0
    for layer in population_layers:
        if layer.population_label == "All":
            continue
        colour = HIGHLIGHT if layer.population_label == "Selected" else PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
        if layer.population_label != "Selected":
            peer_colour_idx += 1
        ids = {u.unit_id for u in layer.units}
        for i, u in enumerate(units):
            if u.unit_id in ids:
                colours[i] = colour
    return colours


def _population_legend_handles(population_layers: list, data_label: str) -> list:
    """Build legend patch handles from population layers."""
    handles = [mpatches.Patch(color=BAR_BLUE, label=data_label)]
    peer_colour_idx = 0
    for layer in population_layers:
        if layer.population_label == "All":
            continue
        if layer.population_label == "Selected":
            handles.append(mpatches.Patch(color=HIGHLIGHT, label="Selected"))
        else:
            colour = PEER_COLOURS[peer_colour_idx % len(PEER_COLOURS)]
            handles.append(mpatches.Patch(color=colour, label=layer.population_label))
            peer_colour_idx += 1
    return handles


def _get_selected_unit(units: list, report_context) -> tuple:
    """Return (index, value, unit) for the selected unit in a sorted unit list."""
    if report_context is None:
        return None, None, None
    for i, u in enumerate(units):
        if u.unit_id == report_context.unit_id:
            return i, u.values[0], u
    return None, None, None


def _selected_layer_value(population_layers: list):
    """Return the Selected layer's first non-null value across the population layers, or None."""
    return next((u.values[0] for layer in population_layers
                 if layer.population_label == "Selected"
                 for u in layer.units if u.values[0] is not None), None)


def _autotable_with_selection(stats: dict, report_context, selected_value) -> dict:
    if report_context is None:
        return stats
    out = dict(stats)
    out["Selected ID"]    = report_context.unit_id
    out["Selected code"]  = report_context.unit_code
    out["Selected name"]  = report_context.unit_name
    out["Selected value"] = round(selected_value, 1) if selected_value is not None else None
    return out
