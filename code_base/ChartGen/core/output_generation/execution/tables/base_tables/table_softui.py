"""
table_softui.py
Base Table -- table_softui. Soft-UI gradient dashboard style: a soft blue
gradient band behind the header row that deliberately bleeds above the
table's own top edge (clip_on=False), rounded white cards per data row,
and a "hero" last-column value rendered as a translucent rounded badge
that deliberately overlaps into the rows above and below it (clip_on=False)
-- accepted, not a bug, the same way ChartGen's existing Base Charts
already draw legends/annotations outside their own axes. Row 0 of
`content` is treated as the header row -- it is the person's own first
grid row, not synthetic content injected by this function.

Standalone artefact, the base_tables equivalent of a Base Chart
(Architecture, Decision 18) -- no imports from ChartGen's own code,
third-party libraries only.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DPI = 450
NARROWER_DIM_INCHES = 7.5

MAX_FONT_SIZE = 12
MIN_FONT_SIZE = 4
FONT_STEP = 0.5
LEFT_PAD_INCHES = 0.08

ACCENT_BLUE_LIGHT = "#6FA3D6"
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


def table_softui(content, column_widths, row_heights, width=80, height=50, tweaks=""):
    p = _prepare(content, column_widths, row_heights, width, height)
    fig, ax = _new_axes(p)
    n_rows, n_cols = p["n_rows"], p["n_cols"]
    fs, lp = p["font_size"], p["left_pad_pct"]
    row_y, col_x = p["row_y"], p["col_x"]
    hero_c = n_cols - 1

    if n_rows > 0:
        header_y0, header_y1 = row_y[0], row_y[1] if len(row_y) > 1 else row_y[0]
        header_h = header_y1 - header_y0
        grad = np.linspace(0, 1, 256).reshape(1, -1)
        ax.imshow(grad, extent=(0, 100, header_y1, header_y0 - header_h * 0.6),
                  aspect="auto", cmap="Blues", alpha=0.5, zorder=0, clip_on=False)
        for c in range(n_cols):
            cx0, cx1, cy0, cy1 = _cell_bounds(p, 0, c)
            val = _cell_text(p, 0, c)
            if c == 0:
                ax.text(cx0 + lp, (cy0 + cy1) / 2, val, ha="left", va="center",
                        fontsize=fs, fontweight="bold", color="#0F4C8A", zorder=2)
            else:
                ax.text(cx1 - lp, (cy0 + cy1) / 2, val, ha="right", va="center",
                        fontsize=fs, fontweight="bold", color="#0F4C8A", zorder=2)

    for r in range(1, n_rows):
        _, _, y0, y1 = _cell_bounds(p, r, 0)
        row_h = y1 - y0
        body_x1 = col_x[hero_c]
        card = mpatches.FancyBboxPatch((0, y0 + row_h * 0.08), body_x1, row_h * 0.84,
                                        boxstyle="round,pad=0,rounding_size=2.4",
                                        linewidth=0, facecolor="white", zorder=1)
        ax.add_patch(card)
        ax.text(lp, (y0 + y1) / 2, _cell_text(p, r, 0), ha="left", va="center",
                fontsize=fs, color="#2F3A45", zorder=2)
        for c in range(1, hero_c):
            cx0, cx1, cy0, cy1 = _cell_bounds(p, r, c)
            ax.text(cx1 - lp, (cy0 + cy1) / 2, _cell_text(p, r, c), ha="right", va="center",
                    fontsize=fs, color=GREY_TEXT, zorder=2)
        hero_val = _cell_text(p, r, hero_c)
        if hero_val:
            hx0, hx1, _, _ = _cell_bounds(p, r, hero_c)
            hero = mpatches.FancyBboxPatch((hx0 + 1, y0 - row_h * 0.35), (hx1 - hx0) - 2, row_h * 1.7,
                                            boxstyle="round,pad=0,rounding_size=3",
                                            linewidth=0, facecolor=ACCENT_BLUE_LIGHT, alpha=0.85,
                                            zorder=3, clip_on=False)
            ax.add_patch(hero)
            ax.text((hx0 + hx1) / 2, (y0 + y1) / 2, hero_val, ha="center", va="center",
                    fontsize=fs, color="white", fontweight="bold", zorder=4, clip_on=False)

    fig.tight_layout(pad=0)
    return _fig_to_bytes(fig)
