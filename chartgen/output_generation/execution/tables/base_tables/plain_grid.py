"""Base Table, plain_grid. A plain grid drawn as one image, first-column text left-aligned, one table-wide font size chosen so the widest first-column entry fits."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DPI = 300
EMU_PER_INCH = 914400

TEXT_SCALE = 5

MAX_FONT_SIZE = 12 * TEXT_SCALE
MIN_FONT_SIZE = 4 * TEXT_SCALE
FONT_STEP = 0.5 * TEXT_SCALE

LEFT_PAD_INCHES = 0.08 * TEXT_SCALE


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _chart_cell_id(cell_text):
    t = (cell_text or "").strip()
    if len(t) > 2 and t.startswith("{") and t.endswith("}"):
        inner = t[1:-1]
        if inner.startswith("C"):
            return inner
    return None


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor="white", edgecolor="none")
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


def _text_height_inches(text, fontsize, dpi):
    if not text:
        return 0.0
    fig = plt.figure(figsize=(1, 1), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    t = ax.text(0, 0, text, fontsize=fontsize)
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


def _shrink_for_multiline_height(font_size, content, row_heights, h_inches, dpi,
                                  min_size=MIN_FONT_SIZE, step=FONT_STEP):
    size = font_size
    while size > min_size:
        fits = True
        for r, row in enumerate(content):
            row_h_pct = row_heights[r] if r < len(row_heights) else 0.0
            available_h = (row_h_pct / 100.0) * h_inches
            for cell_text in row:
                if not cell_text or "\n" not in cell_text:
                    continue
                if _chart_cell_id(cell_text):
                    continue
                if _text_height_inches(cell_text, size, dpi) > available_h:
                    fits = False
                    break
            if not fits:
                break
        if fits:
            return size
        size -= step
    return min_size


def plain_grid(content: list, column_widths: list, row_heights: list,
               width_emu=5486400, height_emu=3429000, tweaks=""):
    n_cols = len(column_widths)

    w_inches, h_inches = _size_to_inches(width_emu, height_emu)

    left_pad_pct = (LEFT_PAD_INCHES / w_inches) * 100 if w_inches else 0.0

    col0_width_pct = column_widths[0] if column_widths else 0.0
    col0_width_inches = (col0_width_pct / 100.0) * w_inches
    available_inches = col0_width_inches - (2 * LEFT_PAD_INCHES)

    col0_texts = [
        row[0] for row in content
        if row and not _chart_cell_id(row[0])
    ]
    font_size = _fit_font_size(col0_texts, available_inches, DPI)
    font_size = _shrink_for_multiline_height(font_size, content, row_heights, h_inches, DPI)

    fig = plt.figure(figsize=(w_inches, h_inches))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.invert_yaxis()
    ax.axis("off")

    col_x = [0.0]
    for cw in column_widths:
        col_x.append(col_x[-1] + cw)
    row_y = [0.0]
    for rh in row_heights:
        row_y.append(row_y[-1] + rh)

    n_rows = len(content)

    chart_cells = {}

    for r in range(n_rows):
        for c in range(n_cols):
            x0 = col_x[c]
            x1 = col_x[c + 1] if c + 1 < len(col_x) else 100.0
            y0 = row_y[r]
            y1 = row_y[r + 1] if r + 1 < len(row_y) else 100.0
            rect = mpatches.Rectangle(
                (x0, y0), x1 - x0, y1 - y0,
                facecolor="white", edgecolor="black", linewidth=0.75 * TEXT_SCALE,
            )
            ax.add_patch(rect)

            row_data = content[r]
            cell_text = row_data[c] if c < len(row_data) else ""

            chart_tag = _chart_cell_id(cell_text)
            if chart_tag:
                chart_cells[chart_tag] = {
                    "x": (x0 / 100.0) * width_emu,
                    "y": (y0 / 100.0) * height_emu,
                    "width": ((x1 - x0) / 100.0) * width_emu,
                    "height": ((y1 - y0) / 100.0) * height_emu,
                }
                continue

            if c == 0:
                ax.text(
                    x0 + left_pad_pct, (y0 + y1) / 2, cell_text,
                    ha="left", va="center", fontsize=font_size, color="black",
                )
            else:
                ax.text(
                    (x0 + x1) / 2, (y0 + y1) / 2, cell_text,
                    ha="center", va="center", fontsize=font_size, color="black",
                )

    return _fig_to_bytes(fig), chart_cells
