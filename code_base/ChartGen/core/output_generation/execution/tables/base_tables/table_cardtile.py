"""
table_cardtile.py
Base Table -- card-tile layout: a bold header row over a stack of
rounded, drop-shadowed "cards", one per data row.

Renders as SVG (matplotlib's own SVG backend, format='svg') rather than
PNG -- the standard rendering methodology across every Base Chart and
Base Table (see Architecture, SVG rendering methodology). Returned bytes
are vector text, not raster, inserted into the PowerPoint via the shared
add_svg_picture dual-blip mechanism rather than a plain add_picture call.

DPI is kept only for matplotlib's own text-metric estimation during
layout (_text_width_inches/_text_height_inches, both still rasterise to a
throwaway offscreen figure to measure text extents) -- it has no bearing
on the final SVG's own resolution, which is vector and scales losslessly.

Font is Calibri (matplotlib.rcParams["font.family"], below) -- ChartGen's
standard chart/table font. svg.fonttype is left at matplotlib's own
default ("path"), which bakes Calibri's actual glyph shapes into vector
outlines at render time, so the result looks correct regardless of what's
installed wherever the SVG is later opened. An alternative ("none", real
live <text> elements) was tried and reverted: neither PowerPoint's own
Find nor either PDF export method exposed the text as genuinely
searchable, and the PDF additionally came out with characters selectable
in mismatched positions/layers -- "path" gives the clean, high-quality
result with no such artefacts, at the accepted cost that table text
isn't searchable/selectable in the final output.

table_inputs contract unchanged: content, column_widths, row_heights,
width, height, tweaks in; bytes out.
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
import matplotlib.patches as mpatches
import numpy as np

DPI = 300
NARROWER_DIM_INCHES = 7.5

MAX_FONT_SIZE = 12
MIN_FONT_SIZE = 4
FONT_STEP = 0.5
LEFT_PAD_INCHES = 0.08

ACCENT_BLUE = "#005EB8"
GREY_LINE = "#C9D2DA"
GREY_TEXT = "#5B6770"

CARD_ROUNDING_INCHES = 0.06
BORDER_WIDTH = 0.375
SHADOW_OFFSET_FRACTION = 0.065
SAVE_PAD_INCHES = 0.03


def _rounded_rect_polygon(x, y, w, h, rx, ry, n=12, **kwargs):
    rx = max(0.0, min(rx, w / 2))
    ry = max(0.0, min(ry, h / 2))

    def arc(cx, cy, a0, a1):
        angs = np.radians(np.linspace(a0, a1, n))
        return np.column_stack([cx + rx * np.cos(angs), cy + ry * np.sin(angs)])

    verts = np.vstack([
        arc(x + rx, y + ry, 180, 270),          # top-left
        arc(x + w - rx, y + ry, 270, 360),      # top-right
        arc(x + w - rx, y + h - ry, 0, 90),     # bottom-right
        arc(x + rx, y + h - ry, 90, 180),       # bottom-left
    ])
    return mpatches.Polygon(verts, closed=True, **kwargs)


def _size_to_inches(width, height):
    s = NARROWER_DIM_INCHES / 100
    return width * s, height * s


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=SAVE_PAD_INCHES,
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


def _text_height_inches(text, fontsize, dpi, fontweight="normal"):
    if not text:
        return 0.0
    fig = plt.figure(figsize=(1, 1), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    t = ax.text(0, 0, text, fontsize=fontsize, fontweight=fontweight)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = t.get_window_extent(renderer=renderer)
    height_in = bbox.height / dpi
    plt.close(fig)
    return height_in


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


def table_cardtile(content, column_widths, row_heights, width=80, height=50, tweaks=""):
    p = _prepare(content, column_widths, row_heights, width, height)
    fig, ax = _new_axes(p)
    n_rows, n_cols = p["n_rows"], p["n_cols"]
    fs, lp = p["font_size"], p["left_pad_pct"]
    full_width = 100.0

    if n_rows > 0:
        _, _, hy0, hy1 = _cell_bounds(p, 0, 0)
        header_y = (hy0 + hy1) / 2
        if n_rows > 1 and p["h_inches"]:
            y_to_inch = p["h_inches"] / 100
            header_text0 = _cell_text(p, 0, 0)
            ht_header = _text_height_inches(header_text0, fs, DPI, fontweight="bold")
            _, _, y0_r1, y1_r1 = _cell_bounds(p, 1, 0)
            row1_text0 = _cell_text(p, 1, 0)
            ht_row1 = _text_height_inches(row1_text0, fs, DPI, fontweight="normal")

            header_center_in = header_y * y_to_inch
            header_bottom_in = header_center_in + ht_header / 2
            row1_center_in = ((y0_r1 + y1_r1) / 2) * y_to_inch
            row1_top_in = row1_center_in - ht_row1 / 2
            gap_in = row1_top_in - header_bottom_in
            delta_in = gap_in / 5
            header_y += delta_in / y_to_inch

        ax.text(lp, header_y, _cell_text(p, 0, 0), ha="left", va="center",
                fontsize=fs, fontweight="bold", color=ACCENT_BLUE)
        for c in range(1, n_cols):
            cx0, cx1, cy0, cy1 = _cell_bounds(p, 0, c)
            ax.text(cx1 - lp, header_y, _cell_text(p, 0, c), ha="right", va="center",
                    fontsize=fs, fontweight="bold", color=ACCENT_BLUE)

    rx = (CARD_ROUNDING_INCHES / p["w_inches"]) * 100 if p["w_inches"] else 0.0
    ry = (CARD_ROUNDING_INCHES / p["h_inches"]) * 100 if p["h_inches"] else 0.0

    for r in range(1, n_rows):
        _, _, y0, y1 = _cell_bounds(p, r, 0)
        row_h = y1 - y0
        card_y = y0 + row_h * 0.1
        card_h = row_h * 0.8
        offset_y = card_h * SHADOW_OFFSET_FRACTION
        offset_x = offset_y * (p["h_inches"] / p["w_inches"]) if p["w_inches"] else offset_y

        shadow = _rounded_rect_polygon(offset_x, card_y + offset_y, full_width, card_h, rx, ry,
                                        linewidth=BORDER_WIDTH, edgecolor=GREY_LINE,
                                        facecolor=GREY_LINE, zorder=1, clip_on=False)
        card = _rounded_rect_polygon(0, card_y, full_width, card_h, rx, ry,
                                      linewidth=BORDER_WIDTH, edgecolor=GREY_LINE,
                                      facecolor="white", zorder=2)
        ax.add_patch(shadow)
        ax.add_patch(card)
        ax.text(lp, (y0 + y1) / 2, _cell_text(p, r, 0), ha="left", va="center",
                fontsize=fs, color="#2F3A45", zorder=3)
        for c in range(1, n_cols):
            cx0, cx1, cy0, cy1 = _cell_bounds(p, r, c)
            ax.text(cx1 - lp, (cy0 + cy1) / 2, _cell_text(p, r, c), ha="right", va="center",
                    fontsize=fs, color=GREY_TEXT, zorder=3)

    fig.tight_layout(pad=0)
    return _fig_to_bytes(fig)
