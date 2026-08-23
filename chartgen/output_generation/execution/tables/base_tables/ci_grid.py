"""Base Table, ci_grid. CI-style variant of plain_grid. Rows 0 and 1 are both header rows. The final two columns carry the fixed text Benchmark, Target and Met(?), never content. A body row whose every cell is blank draws nothing, but still occupies its height."""

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

HEADER_ROWS = 2
MERGED_HEADER_LABEL = "Benchmark"
SUB_HEADINGS = ["Target", "Met(?)"]
HEADER_BG = "white"
HEADER_TEXT_COLOUR = "#1F2A33"
HEADER_FONT_BOOST = 2 * TEXT_SCALE
HEADER_ROW_HEIGHT_REDUCTION = 1 / 3


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _chart_cell_id(cell_text):
    t = (cell_text or "").strip()
    if len(t) > 2 and t.startswith("{") and t.endswith("}"):
        inner = t[1:-1]
        if inner.startswith("C"):
            return inner
    return None


def _row_is_blank(row, n_cols):
    for c in range(n_cols):
        cell = row[c] if c < len(row) else ""
        if (cell or "").strip():
            return False
    return True


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


def _shrink_for_multiline_height(font_size, body_content, body_row_heights, h_inches, dpi,
                                  min_size=MIN_FONT_SIZE, step=FONT_STEP):
    size = font_size
    while size > min_size:
        fits = True
        for r, row in enumerate(body_content):
            row_h_pct = body_row_heights[r] if r < len(body_row_heights) else 0.0
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


def _adjusted_row_heights(row_heights, header_rows=HEADER_ROWS, reduction=HEADER_ROW_HEIGHT_REDUCTION):
    if len(row_heights) <= header_rows:
        return list(row_heights)
    header_part = row_heights[:header_rows]
    body_part = row_heights[header_rows:]
    header_total = sum(header_part)
    body_total = sum(body_part)
    freed = header_total * reduction
    new_header_part = [h * (1 - reduction) for h in header_part]
    if body_total > 0:
        scale = (body_total + freed) / body_total
        new_body_part = [h * scale for h in body_part]
    else:
        new_body_part = list(body_part)
    return new_header_part + new_body_part


def ci_grid(content: list, column_widths: list, row_heights: list,
            width_emu=5486400, height_emu=3429000, tweaks=""):
    n_cols = len(column_widths)
    n_rows = len(content)
    w_inches, h_inches = _size_to_inches(width_emu, height_emu)
    left_pad_pct = (LEFT_PAD_INCHES / w_inches) * 100 if w_inches else 0.0

    row_heights = _adjusted_row_heights(row_heights)

    col0_width_pct = column_widths[0] if column_widths else 0.0
    col0_width_inches = (col0_width_pct / 100.0) * w_inches
    available_inches = col0_width_inches - (2 * LEFT_PAD_INCHES)

    body_content = content[HEADER_ROWS:]
    body_row_heights = row_heights[HEADER_ROWS:]

    col0_texts = [row[0] for row in body_content if row and not _chart_cell_id(row[0])]
    font_size = _fit_font_size(col0_texts, available_inches, DPI)
    font_size = _shrink_for_multiline_height(font_size, body_content, body_row_heights, h_inches, DPI)

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

    chart_cells = {}

    if n_rows >= HEADER_ROWS and n_cols > 0:
        header_top = row_y[0]
        header_bottom = row_y[HEADER_ROWS] if HEADER_ROWS < len(row_y) else 100.0
        header_row0 = content[0] if len(content) > 0 else []

        last_two_start = max(n_cols - 2, 0)
        merge_last_two = n_cols > 2

        for c in range(n_cols):
            x0 = col_x[c]
            x1 = col_x[c + 1] if c + 1 < len(col_x) else 100.0

            if c < last_two_start or not merge_last_two:
                rect = mpatches.Rectangle((x0, header_top), x1 - x0, header_bottom - header_top,
                                           facecolor=HEADER_BG, edgecolor="black", linewidth=0.75 * TEXT_SCALE)
                ax.add_patch(rect)
                cell_text = header_row0[c] if c < len(header_row0) else ""
                chart_tag = _chart_cell_id(cell_text)
                if chart_tag:
                    chart_cells[chart_tag] = {
                        "x": (x0 / 100.0) * width_emu, "y": (header_top / 100.0) * height_emu,
                        "width": ((x1 - x0) / 100.0) * width_emu,
                        "height": ((header_bottom - header_top) / 100.0) * height_emu,
                    }
                    continue
                ha = "left" if c == 0 else "center"
                text_x = x0 + left_pad_pct if c == 0 else (x0 + x1) / 2
                ax.text(text_x, (header_top + header_bottom) / 2, cell_text,
                        ha=ha, va="center", fontsize=font_size + HEADER_FONT_BOOST, fontweight="bold",
                        color=HEADER_TEXT_COLOUR)
            elif c == last_two_start:
                row0_y1 = row_y[1] if len(row_y) > 1 else header_bottom
                merged_x1 = col_x[last_two_start + 2] if last_two_start + 2 < len(col_x) else 100.0
                rect_merged = mpatches.Rectangle((x0, header_top), merged_x1 - x0, row0_y1 - header_top,
                                                  facecolor=HEADER_BG, edgecolor="black", linewidth=0.75 * TEXT_SCALE)
                ax.add_patch(rect_merged)
                ax.text((x0 + merged_x1) / 2, (header_top + row0_y1) / 2, MERGED_HEADER_LABEL,
                        ha="center", va="center", fontsize=font_size + HEADER_FONT_BOOST, fontweight="bold",
                        color=HEADER_TEXT_COLOUR)

                row1_y1 = row_y[2] if len(row_y) > 2 else header_bottom
                rect1 = mpatches.Rectangle((x0, row0_y1), x1 - x0, row1_y1 - row0_y1,
                                            facecolor=HEADER_BG, edgecolor="black", linewidth=0.75 * TEXT_SCALE)
                ax.add_patch(rect1)
                sub_heading = SUB_HEADINGS[0] if SUB_HEADINGS else ""
                ax.text((x0 + x1) / 2, (row0_y1 + row1_y1) / 2, sub_heading,
                        ha="center", va="center", fontsize=font_size, fontweight="bold",
                        color=HEADER_TEXT_COLOUR)
            else:
                row0_y1 = row_y[1] if len(row_y) > 1 else header_bottom
                row1_y1 = row_y[2] if len(row_y) > 2 else header_bottom
                rect1 = mpatches.Rectangle((x0, row0_y1), x1 - x0, row1_y1 - row0_y1,
                                            facecolor=HEADER_BG, edgecolor="black", linewidth=0.75 * TEXT_SCALE)
                ax.add_patch(rect1)
                idx = c - last_two_start
                sub_heading = SUB_HEADINGS[idx] if idx < len(SUB_HEADINGS) else ""
                ax.text((x0 + x1) / 2, (row0_y1 + row1_y1) / 2, sub_heading,
                        ha="center", va="center", fontsize=font_size, fontweight="bold",
                        color=HEADER_TEXT_COLOUR)

    for r in range(HEADER_ROWS, n_rows):
        row_data = content[r]
        if not _row_is_blank(row_data, n_cols):
            y0 = row_y[r]
            y1 = row_y[r + 1] if r + 1 < len(row_y) else 100.0
            for c in range(n_cols):
                x0 = col_x[c]
                x1 = col_x[c + 1] if c + 1 < len(col_x) else 100.0
                rect = mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0,
                                           facecolor="white", edgecolor="black", linewidth=0.75 * TEXT_SCALE)
                ax.add_patch(rect)

                cell_text = row_data[c] if c < len(row_data) else ""
                chart_tag = _chart_cell_id(cell_text)
                if chart_tag:
                    chart_cells[chart_tag] = {
                        "x": (x0 / 100.0) * width_emu, "y": (y0 / 100.0) * height_emu,
                        "width": ((x1 - x0) / 100.0) * width_emu,
                        "height": ((y1 - y0) / 100.0) * height_emu,
                    }
                    continue
                if c == 0:
                    ax.text(x0 + left_pad_pct, (y0 + y1) / 2, cell_text,
                            ha="left", va="center", fontsize=font_size, color="black")
                else:
                    ax.text((x0 + x1) / 2, (y0 + y1) / 2, cell_text,
                            ha="center", va="center", fontsize=font_size, color="black")

    return _fig_to_bytes(fig), chart_cells
