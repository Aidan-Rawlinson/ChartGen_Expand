"""Base Table, ci_cardtile. CI-style variant of table_cardtile. Rows 0 and 1 are both header rows under one rounded block. The final two columns carry the fixed text Benchmark, Target and Met(?), never content. A body row whose every cell is blank draws no card, but still occupies its height."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

DPI = 300
EMU_PER_INCH = 914400

TEXT_SCALE = 5

MAX_FONT_SIZE = 12 * TEXT_SCALE
MIN_FONT_SIZE = 4 * TEXT_SCALE
FONT_STEP = 0.5 * TEXT_SCALE
LEFT_PAD_INCHES = 0.08 * TEXT_SCALE

ACCENT_BLUE = "#1265A5"
GREY_LINE = "#C9D2DA"
GREY_TEXT = "#5B6770"
HEADER_BG = "#FCFEFF"
HEADER_BG_GRADIENT_START = "#DEEEF9"

CARD_ROUNDING_INCHES = 0.06 * TEXT_SCALE
BORDER_WIDTH = 0.375 * TEXT_SCALE
SHADOW_OFFSET_FRACTION = 0.065
SAVE_PAD_INCHES = 0.03 * TEXT_SCALE
CARD_HEIGHT_FRACTION = 0.8

HEADER_ROWS = 2
MERGED_HEADER_LABEL = "Benchmark"
SUB_HEADINGS = ["Target", "Met(?)"]
HEADER_FONT_BOOST = 2 * TEXT_SCALE
CENTRED_BODY_COLUMN_INDEX = 3
HEADER_ROW_HEIGHT_REDUCTION = 1 / 3


def _rounded_rect_polygon(x, y, w, h, rx, ry, n=12, **kwargs):
    rx = max(0.0, min(rx, w / 2))
    ry = max(0.0, min(ry, h / 2))

    def arc(cx, cy, a0, a1):
        angs = np.radians(np.linspace(a0, a1, n))
        return np.column_stack([cx + rx * np.cos(angs), cy + ry * np.sin(angs)])

    verts = np.vstack([
        arc(x + rx, y + ry, 180, 270),
        arc(x + w - rx, y + ry, 270, 360),
        arc(x + w - rx, y + h - ry, 0, 90),
        arc(x + rx, y + h - ry, 90, 180),
    ])
    return mpatches.Polygon(verts, closed=True, **kwargs)


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
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=SAVE_PAD_INCHES,
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _resolve_chart_cells(fig, chart_cells_raw: dict, w_inches: float, h_inches: float,
                          width_emu: int, height_emu: int) -> dict:
    if not chart_cells_raw:
        return {}

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    tight_bbox = fig.get_tightbbox(renderer)

    crop_left_in = tight_bbox.x0 - SAVE_PAD_INCHES
    crop_top_in = tight_bbox.y0 - SAVE_PAD_INCHES
    total_w_in = (tight_bbox.x1 - tight_bbox.x0) + 2 * SAVE_PAD_INCHES
    total_h_in = (tight_bbox.y1 - tight_bbox.y0) + 2 * SAVE_PAD_INCHES

    chart_cells = {}
    for tag, (cx0, cx1, cy0, cy1) in chart_cells_raw.items():
        fig_x0 = (cx0 / 100.0) * w_inches
        fig_x1 = (cx1 / 100.0) * w_inches
        fig_y0 = (cy0 / 100.0) * h_inches
        fig_y1 = (cy1 / 100.0) * h_inches

        frac_x0 = (fig_x0 - crop_left_in) / total_w_in if total_w_in else 0.0
        frac_x1 = (fig_x1 - crop_left_in) / total_w_in if total_w_in else 0.0
        frac_y0 = (fig_y0 - crop_top_in) / total_h_in if total_h_in else 0.0
        frac_y1 = (fig_y1 - crop_top_in) / total_h_in if total_h_in else 0.0

        chart_cells[tag] = {
            "x": frac_x0 * width_emu, "y": frac_y0 * height_emu,
            "width": (frac_x1 - frac_x0) * width_emu,
            "height": (frac_y1 - frac_y0) * height_emu,
        }
    return chart_cells


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


def _shrink_for_multiline_height(font_size, body_content, body_row_heights, h_inches, dpi,
                                  min_size=MIN_FONT_SIZE, step=FONT_STEP):
    size = font_size
    while size > min_size:
        fits = True
        for r, row in enumerate(body_content):
            row_h_pct = body_row_heights[r] if r < len(body_row_heights) else 0.0
            row_h_in = (row_h_pct / 100.0) * h_inches
            available_h = row_h_in * CARD_HEIGHT_FRACTION
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


def _prepare(content, column_widths, row_heights, width_emu, height_emu):
    n_cols = len(column_widths)
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
    fig = plt.figure(figsize=(p["w_inches"], p["h_inches"]))
    ax = fig.add_axes([0, 0, 1, 1])
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


def ci_cardtile(content, column_widths, row_heights, width_emu=5486400, height_emu=3429000, tweaks=""):
    p = _prepare(content, column_widths, row_heights, width_emu, height_emu)
    fig, ax = _new_axes(p)
    n_rows, n_cols = p["n_rows"], p["n_cols"]
    fs, lp = p["font_size"], p["left_pad_pct"]
    full_width = 100.0

    chart_cells_raw = {}

    def _record_chart_cell(chart_tag, cx0, cx1, cy0, cy1):
        chart_cells_raw[chart_tag] = (cx0, cx1, cy0, cy1)

    rx = (CARD_ROUNDING_INCHES / p["w_inches"]) * 100 if p["w_inches"] else 0.0
    ry = (CARD_ROUNDING_INCHES / p["h_inches"]) * 100 if p["h_inches"] else 0.0

    row_y_all = p["row_y"]
    if n_rows > HEADER_ROWS and HEADER_ROWS + 1 < len(row_y_all):
        ref_row_h = row_y_all[HEADER_ROWS + 1] - row_y_all[HEADER_ROWS]
    else:
        ref_row_h = row_y_all[-1] - row_y_all[0] if len(row_y_all) > 1 else 0.0
    ref_card_h = ref_row_h * CARD_HEIGHT_FRACTION
    shadow_offset_y = ref_card_h * SHADOW_OFFSET_FRACTION
    shadow_offset_x = shadow_offset_y * (p["h_inches"] / p["w_inches"]) if p["w_inches"] else shadow_offset_y

    if n_rows >= HEADER_ROWS and n_cols > 0:
        row_y = p["row_y"]
        col_x = p["col_x"]
        header_top = row_y[0]
        header_bottom_full = row_y[HEADER_ROWS] if HEADER_ROWS < len(row_y) else 100.0
        header_full_h = header_bottom_full - header_top

        header_offset_y = shadow_offset_y
        header_offset_x = shadow_offset_x
        lift = header_offset_y / 2
        header_block_h = header_full_h - header_offset_y
        header_bottom = header_top + header_block_h

        header_centre = (header_top + header_bottom) / 2
        row0_bottom = (row_y[1] if len(row_y) > 1 else header_bottom_full) - lift
        row0_centre = (header_top + row0_bottom) / 2
        row1_centre = (row0_bottom + header_bottom) / 2
        last_two_start = max(n_cols - 2, 0)
        merge_last_two = n_cols > 2

        header_shadow = _rounded_rect_polygon(
            header_offset_x, header_top + header_offset_y, full_width, header_block_h,
            rx, ry, linewidth=BORDER_WIDTH, edgecolor=GREY_LINE, facecolor=GREY_LINE,
            zorder=1, clip_on=False,
        )
        ax.add_patch(header_shadow)

        header_fade = mcolors.LinearSegmentedColormap.from_list(
            "header_fade", [HEADER_BG_GRADIENT_START, HEADER_BG])
        header_gradient_data = np.linspace(0, 1, 256).reshape(1, -1)
        header_clip_shape = _rounded_rect_polygon(0, header_top, full_width, header_block_h, rx, ry)
        header_im = ax.imshow(
            header_gradient_data, extent=[0, full_width, header_top, header_top + header_block_h],
            origin="lower", aspect="auto", cmap=header_fade, zorder=2,
        )
        header_im.set_clip_path(header_clip_shape.get_path(), transform=ax.transData)

        header_border = _rounded_rect_polygon(
            0, header_top, full_width, header_block_h, rx, ry,
            linewidth=BORDER_WIDTH, edgecolor=GREY_LINE, facecolor="none", zorder=2.5,
        )
        ax.add_patch(header_border)

        for c in range(n_cols):
            x0 = col_x[c]
            x1 = col_x[c + 1] if c + 1 < len(col_x) else 100.0

            if c < last_two_start or not merge_last_two:
                cell_text = _cell_text(p, 0, c)
                chart_tag = _chart_cell_id(cell_text)
                if chart_tag:
                    _record_chart_cell(chart_tag, x0, x1, header_top, header_bottom)
                    continue
                if c == 0:
                    ax.text(lp, header_centre, cell_text, ha="left", va="center",
                            fontsize=fs + HEADER_FONT_BOOST, fontweight="bold", color=ACCENT_BLUE, zorder=3)
                else:
                    ax.text((x0 + x1) / 2, header_centre, cell_text, ha="center", va="center",
                            fontsize=fs + HEADER_FONT_BOOST, fontweight="bold", color=ACCENT_BLUE, zorder=3)

        if merge_last_two:
            merged_x0 = col_x[last_two_start]
            merged_x1 = col_x[last_two_start + 2] if last_two_start + 2 < len(col_x) else full_width
            ax.text((merged_x0 + merged_x1) / 2, row0_centre, MERGED_HEADER_LABEL,
                    ha="center", va="center", fontsize=fs + HEADER_FONT_BOOST, fontweight="bold",
                    color=ACCENT_BLUE, zorder=3)
            for i, c in enumerate(range(last_two_start, n_cols)):
                if i >= len(SUB_HEADINGS):
                    break
                x0 = col_x[c]
                x1 = col_x[c + 1] if c + 1 < len(col_x) else full_width
                ax.text((x0 + x1) / 2, row1_centre, SUB_HEADINGS[i],
                        ha="center", va="center", fontsize=fs, fontweight="bold",
                        color=ACCENT_BLUE, zorder=3)

    for r in range(HEADER_ROWS, n_rows):
        row_data = p["content"][r]
        if _row_is_blank(row_data, n_cols):
            continue

        _, _, y0, y1 = _cell_bounds(p, r, 0)
        row_h = y1 - y0
        card_y = y0 + row_h * 0.1
        card_h = row_h * CARD_HEIGHT_FRACTION
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

        cx0_col0, cx1_col0, _, _ = _cell_bounds(p, r, 0)
        body0_val = _cell_text(p, r, 0)
        body0_tag = _chart_cell_id(body0_val)
        if body0_tag:
            _record_chart_cell(body0_tag, cx0_col0, cx1_col0, card_y, card_y + card_h)
        else:
            ax.text(lp, (y0 + y1) / 2, body0_val, ha="left", va="center",
                    fontsize=fs, color="#2F3A45", zorder=3)
        for c in range(1, n_cols):
            cx0, cx1, cy0, cy1 = _cell_bounds(p, r, c)
            body_val = _cell_text(p, r, c)
            body_tag = _chart_cell_id(body_val)
            if body_tag:
                _record_chart_cell(body_tag, cx0, cx1, card_y, card_y + card_h)
                continue
            if c == CENTRED_BODY_COLUMN_INDEX:
                ax.text((cx0 + cx1) / 2, (cy0 + cy1) / 2, body_val, ha="center", va="center",
                        fontsize=fs, color=GREY_TEXT, zorder=3)
            else:
                ax.text(cx1 - lp, (cy0 + cy1) / 2, body_val, ha="right", va="center",
                        fontsize=fs, color=GREY_TEXT, zorder=3)

    chart_cells = _resolve_chart_cells(
        fig, chart_cells_raw, p["w_inches"], p["h_inches"], width_emu, height_emu,
    )
    return _fig_to_bytes(fig), chart_cells
