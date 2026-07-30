"""
table_editorial.py
Base Table -- table_editorial. Editorial rule-based style (FT/Economist
influence) -- no vertical rules at all, a heavy rule above the header and
below the last row, a thin rule under the header. Row 0 of `content` is
treated as the header row -- it is the person's own first grid row, not
synthetic content injected by this function.

Standalone artefact, the base_tables equivalent of a Base Chart
(Architecture, Decision 18) -- no imports from ChartGen's own code,
third-party libraries only.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DPI = 450
NARROWER_DIM_INCHES = 7.5

MAX_FONT_SIZE = 12
MIN_FONT_SIZE = 4
FONT_STEP = 0.5
LEFT_PAD_INCHES = 0.08

GREY_TEXT = "#5B6770"


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


def _text_width_inches(text, fontsize, dpi):
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


def _fit_font_size(texts, available_width_inches, dpi,
                    max_size=MAX_FONT_SIZE, min_size=MIN_FONT_SIZE, step=FONT_STEP):
    non_empty = [t for t in texts if t]
    if not non_empty or available_width_inches <= 0:
        return min_size
    size = max_size
    while size > min_size:
        widest = max(_text_width_inches(t, size, dpi) for t in non_empty)
        if widest <= available_width_inches:
            return size
        size -= step
    return min_size


def _prepare(content, column_widths, row_heights, width, height):
    n_cols = len(column_widths)
    w_inches, h_inches = _size_to_inches(width, height)
    left_pad_pct = (LEFT_PAD_INCHES / w_inches) * 100 if w_inches else 0.0

    col0_width_pct = column_widths[0] if column_widths else 0.0
    col0_width_inches = (col0_width_pct / 100.0) * w_inches
    available_inches = col0_width_inches - (2 * LEFT_PAD_INCHES)

    col0_texts = [row[0] if row else "" for row in content]
    font_size = _fit_font_size(col0_texts, available_inches, DPI)

    col_x = [0.0]
    for cw in column_widths:
        col_x.append(col_x[-1] + cw)
    row_y = [0.0]
    for rh in row_heights:
        row_y.append(row_y[-1] + rh)

    return {
        "content": [list(row) for row in content],
        "col_x": col_x, "row_y": row_y,
        "w_inches": w_inches, "h_inches": h_inches,
        "font_size": font_size, "left_pad_pct": left_pad_pct,
        "n_cols": n_cols, "n_rows": len(content),
    }


def _new_axes(p):
    fig, ax = plt.subplots(figsize=(p["w_inches"], p["h_inches"]))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.invert_yaxis()
    ax.axis("off")
    return fig, ax


def _cell_bounds(p, r, c):
    col_x, row_y = p["col_x"], p["row_y"]
    x0 = col_x[c]
    x1 = col_x[c + 1] if c + 1 < len(col_x) else 100.0
    y0 = row_y[r]
    y1 = row_y[r + 1] if r + 1 < len(row_y) else 100.0
    return x0, x1, y0, y1


def _cell_text(p, r, c):
    row = p["content"][r]
    return row[c] if c < len(row) else ""


def table_editorial(content, column_widths, row_heights, width=80, height=50, tweaks=""):
    p = _prepare(content, column_widths, row_heights, width, height)
    fig, ax = _new_axes(p)
    n_rows, n_cols = p["n_rows"], p["n_cols"]
    fs, lp = p["font_size"], p["left_pad_pct"]
    row_y = p["row_y"]
    span = row_y[-1] - row_y[0]

    ax.plot([0, 100], [row_y[0] - span * 0.01, row_y[0] - span * 0.01], color="black", lw=2.2)
    if n_rows > 1:
        ax.plot([0, 100], [row_y[1], row_y[1]], color=GREY_TEXT, lw=0.7)
    ax.plot([0, 100], [row_y[-1] + span * 0.01, row_y[-1] + span * 0.01], color="black", lw=2.2)

    for r in range(n_rows):
        bold = (r == 0)
        for c in range(n_cols):
            cx0, cx1, cy0, cy1 = _cell_bounds(p, r, c)
            val = _cell_text(p, r, c)
            if c == 0:
                ax.text(cx0 + lp, (cy0 + cy1) / 2, val, ha="left", va="center",
                        fontsize=fs, fontweight="bold" if bold else "normal")
            else:
                ax.text(cx1 - lp, (cy0 + cy1) / 2, val, ha="right", va="center",
                        fontsize=fs, fontweight="bold" if bold else "normal")

    fig.tight_layout(pad=0)
    return _fig_to_bytes(fig)
