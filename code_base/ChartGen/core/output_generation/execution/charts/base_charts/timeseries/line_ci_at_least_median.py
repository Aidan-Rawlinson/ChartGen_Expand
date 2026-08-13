"""
line_ci_at_least_median.py
Base Chart -- TimeSeries, diagnostic variant, one of the "CI" family
alongside line_ci_at_most_median/line_ci_at_most_2/line_ci_at_most_5pct/
line_ci_0/line_ci_at_least_90pct/line_ci_100pct. Three-way indicator, all
checking only the Selected unit's own submission value in the FINAL
period (never any other period):

  - blue circle, white tick    -- passes: (final submission value +
                                  0.0001) >= the final period's population
                                  median (from the scope/"All" layer,
                                  population_layers[0])
  - orange circle, white cross -- fails that same check
  - grey circle, white dash    -- no submission value for the final
                                  period at all (or no median to compare
                                  against), so pass/fail can't be
                                  evaluated

The circle's own fill colour carries the pass/fail/no-data signal; the
symbol inside it is always white, never the fill's own colour scheme.
The fail colour is a genuine complement of the pass colour -- same HLS
lightness/saturation as the blue, opposite hue -- not just "an orange"
picked freehand.

The +0.0001 is deliberate, not a floating-point tolerance in the usual
"isclose" sense -- a value exactly equal to the median is meant to pass,
and this is the specified way to make that so under float comparison.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width_emu,
height_emu, tweaks) -- no report_context or any other runtime object.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt

EMU_PER_INCH = 914400

CIRCLE_FILL_PASS = "#7CB9E8"     # sparkline1's own MEDIAN_COL blue
CIRCLE_FILL_FAIL = "#E8AB7C"     # complementary to CIRCLE_FILL_PASS -- same HLS lightness/saturation, opposite hue (206deg -> 26deg)
CIRCLE_FILL_NO_DATA = "#C1C8CE"  # same light grey as line_has_data's own circle
MARK_COLOUR = "white"

CIRCLE_DIAMETER_FRACTION = 0.72  # matches line_has_data's own current sizing

EPSILON = 0.0001


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor="none", edgecolor="none",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _final_submission_value(population_layers):
    """The Selected unit's own value for the final period only -- None if
    there's no Selected layer, no submission unit, an empty values list,
    or the final entry itself is None."""
    for layer in population_layers[1:] if population_layers else []:
        if getattr(layer, "population_label", None) != "Selected":
            continue
        layer_metric = layer.metrics[0] if layer.metrics else None
        if layer_metric is None:
            continue
        unit = layer_metric.units[0] if layer_metric.units else None
        if unit is not None and unit.values:
            return unit.values[-1]
    return None


def _final_median(population_layers):
    """The scope layer's (population_layers[0]) own median for the final
    period -- None if there's no scope layer, no metric, or no
    period_stats to read it from."""
    if not population_layers:
        return None
    base = population_layers[0]
    metric = base.metrics[0] if base.metrics else None
    if metric is None or not metric.period_stats:
        return None
    return metric.period_stats[-1].median


def _draw_mark(ax, cx, cy, r, result):
    lw = max(1.2, r * 72 * 0.12)
    if result == "pass":
        p1 = (cx - 0.5 * r, cy - 0.05 * r)
        p2 = (cx - 0.1 * r, cy - 0.45 * r)
        p3 = (cx + 0.55 * r, cy + 0.45 * r)
        ax.plot([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round",
                solid_joinstyle="round", zorder=2)
    elif result == "fail":
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy - 0.4 * r, cy + 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy + 0.4 * r, cy - 0.4 * r],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)
    else:  # "no_data"
        ax.plot([cx - 0.4 * r, cx + 0.4 * r], [cy, cy],
                color=MARK_COLOUR, linewidth=lw, solid_capstyle="round", zorder=2)


def line_ci_at_least_median(population_layers: list, width_emu=2736215, height_emu=684054, tweaks=""):
    w_in, h_in = _size_to_inches(width_emu, height_emu)

    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.axis("off")

    cx, cy = w_in / 2, h_in / 2
    r = (min(w_in, h_in) / 2) * CIRCLE_DIAMETER_FRACTION

    final_value = _final_submission_value(population_layers)
    final_median = _final_median(population_layers)

    if final_value is None or final_median is None:
        result = "no_data"
    elif (final_value + EPSILON) >= final_median:
        result = "pass"
    else:
        result = "fail"

    circle_fill = {"pass": CIRCLE_FILL_PASS, "fail": CIRCLE_FILL_FAIL,
                   "no_data": CIRCLE_FILL_NO_DATA}[result]
    circle = plt.Circle((cx, cy), r, facecolor=circle_fill, edgecolor="none", zorder=1)
    ax.add_patch(circle)

    _draw_mark(ax, cx, cy, r, result)

    return _fig_to_bytes(fig)
