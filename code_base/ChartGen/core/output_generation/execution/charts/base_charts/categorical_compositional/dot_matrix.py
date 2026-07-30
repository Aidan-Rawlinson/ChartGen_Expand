"""
dot_matrix.py
Base Chart — CategoricalCompositional. Dot matrix, filled dots per category
per question, each dot approx. 10%. Population layers not applicable —
renders population-level aggregates.

Standalone artefact: no imports from ChartGen's own code, third-party
libraries only. Receives chart_inputs only (population_layers, width,
height, tweaks).
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font, baked into the SVG
# vector output as real glyph outlines (svg.fonttype default "path").
# See Architecture, SVG rendering methodology.
matplotlib.rcParams["font.family"] = "Calibri"
import matplotlib.pyplot as plt

YES_COL = "#4CAF50"
NO_COL  = "#C0392B"
PIE_COLOURS = ["#1F4E79", "#E87722", "#7030A0", "#2E86AB", "#F0A500", "#4CAF50"]

NARROWER_DIM_INCHES = 7.5


def _size_to_inches(width, height):
    s = NARROWER_DIM_INCHES / 100
    return width * s, height * s


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def dot_matrix(population_layers: list, width=80, height=55, tweaks=""):
    """Dot matrix — filled dots per category per question, each dot ≈ 10%."""
    base = population_layers[0]
    w, h = _size_to_inches(width, height)
    is_yn = (len(base.metrics) > 1 and
             base.metrics[0].category_names == ["Yes", "No"])
    if is_yn:
        metrics = base.metrics
        categories = ["Yes", "No"]
        counts_list = [m.stats.component_counts for m in metrics]
        totals = [m.stats.count_with_data or 1 for m in metrics]
        questions = [m.name or "" for m in metrics]
    else:
        metric = base.metrics[0]
        categories = metric.category_names
        counts_list = [metric.stats.component_counts]
        totals = [metric.stats.count_with_data or 1]
        questions = [metric.name or ""]

    n_q = len(questions)
    n_c = len(categories)
    fig, ax = plt.subplots(figsize=(w, h))
    colours_use = [YES_COL, NO_COL] if is_yn else PIE_COLOURS[:n_c]

    for qi, (q, counts, total) in enumerate(zip(questions, counts_list, totals)):
        pcts = [(c / total * 100) if c else 0 for c in counts]
        for ci, (cat, pct, col) in enumerate(zip(categories, pcts, colours_use)):
            n_filled = round(pct / 10)
            for d in range(10):
                filled = d < n_filled
                ax.scatter(ci * 11 + d, qi,
                           s=55, color=col if filled else "#E0E0E0",
                           zorder=2, linewidths=0)

    ax.set_yticks(range(n_q)); ax.set_yticklabels(questions, fontsize=7)
    ax.invert_yaxis()
    ax.set_xticks([ci * 11 + 4.5 for ci in range(n_c)])
    ax.set_xticklabels(categories, fontsize=8, fontweight="bold")
    ax.tick_params(bottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(False); ax.set_facecolor("white")
    ax.text(0, n_q + 0.3, "Each dot ≈ 10%", fontsize=6.5, color="#888888", style="italic")
    fig.tight_layout()
    return _fig_to_bytes(fig)
