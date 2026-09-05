"""Base Table, ci_cardtile2. CI-style variant of table_cardtile for three content columns: indicator id, description, and the sparkline. Drawn to a fixed design rather than fitted to its input. Row height is a constant, set so a table of 23.5 row units fills the shape exactly; row_heights is accepted but ignored, so a shorter table finishes short of the bottom rather than stretching, and a longer one overruns visibly. Every font size is a fixed number of points. Row 0 is the single header row; row 1 onwards is body. Header cells 1 and 2 are bold, cell 1 centred and cell 2 left aligned, and cell 3 is normal weight and a point smaller. Body rows draw column 1 centred and bold, column 2 left aligned and normal weight, and every later column right aligned, with a very light grey band behind column 1 and vertical grey rules either side of column 2. Column 2's own authored line breaks are drawn exactly as given, with no re-wrapping or re-optimising of any kind. A body row with no chart marker in column 3 is a sub-heading row: half height, a pale blue band across the full width, all text bold and left aligned and nudged down so all-caps text sits optically centred, and no column banding. A sub-heading-shaped row with no text at all in any column is blank instead: it costs no height at all, drawing no band, no rule and no text, so the table's own border and rounded bottom corners close immediately after the last row that actually has something in it, and any blank rows simply add no further length. Every other row's height, and the overall image size, are unaffected by how many blank rows are present."""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

EMU_PER_INCH = 914400
POINTS_PER_INCH = 72.0

TEXT_SCALE = 5

LEFT_PAD_INCHES = 0.08 * TEXT_SCALE

ACCENT_BLUE = "#1265A5"
GREY_LINE = "#87929C"
GREY_TEXT = "#5B6770"
BODY_TEXT = "#2F3A45"
HEADER_BG = "#DEEEF9"
COLUMN1_BG = "#F5F7F8"
SUBHEADING_BG = "#EDF6FC"

TABLE_ROUNDING_INCHES = 0.06 * TEXT_SCALE
LINE_WIDTH = 0.5 * TEXT_SCALE

ROW_UNITS_AT_FULL_HEIGHT = 23.5
FULL_ROW_HEIGHT_PCT = 100.0 / ROW_UNITS_AT_FULL_HEIGHT
SUBHEADING_ROW_HEIGHT_FACTOR = 0.5

HEADER_ROWS = 1
HEADER_BOLD_FONT_SIZE = 9 * TEXT_SCALE
HEADER_PLAIN_FONT_SIZE = 8 * TEXT_SCALE
HEADER_PLAIN_COLUMN_INDEX = 2
HEADER_LEFT_COLUMN_INDICES = (1,)

ID_FONT_SIZE = 7 * TEXT_SCALE
BODY_FONT_SIZE = 7 * TEXT_SCALE
SUBHEADING_FONT_SIZE = 8 * TEXT_SCALE
SUBHEADING_NUDGE_EM = 0.07

BODY_COLUMN_ALIGNMENTS = {0: "center", 1: "left"}
BODY_DEFAULT_ALIGNMENT = "right"
BANDED_COLUMN_INDEX = 0
RULED_COLUMN_INDEX = 1
CHART_COLUMN_INDEX = 2


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


def _points_to_data_x(points, w_inches):
    return (points / POINTS_PER_INCH) / w_inches * 100.0 if w_inches else 0.0


def _points_to_data_y(points, h_inches):
    return (points / POINTS_PER_INCH) / h_inches * 100.0 if h_inches else 0.0


def _chart_cell_id(cell_text):
    t = (cell_text or "").strip()
    if len(t) > 2 and t.startswith("{") and t.endswith("}"):
        inner = t[1:-1]
        if inner.startswith("C"):
            return inner
    return None


def _is_subheading_row(row):
    if CHART_COLUMN_INDEX >= len(row):
        return True
    return _chart_cell_id(row[CHART_COLUMN_INDEX]) is None


def _row_is_blank(row):
    return all(not (cell or "").strip() for cell in row)


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _resolve_chart_cells(chart_cells_raw: dict, width_emu: int, height_emu: int) -> dict:
    chart_cells = {}
    for tag, (cx0, cx1, cy0, cy1) in chart_cells_raw.items():
        x0 = (cx0 / 100.0) * width_emu
        x1 = (cx1 / 100.0) * width_emu
        y0 = (cy0 / 100.0) * height_emu
        y1 = (cy1 / 100.0) * height_emu
        chart_cells[tag] = {
            "x": x0, "y": y0,
            "width": x1 - x0, "height": y1 - y0,
        }
    return chart_cells


def _drawn_row_heights(content):
    drawn = []
    subheading = []
    for r, row in enumerate(content):
        if r < HEADER_ROWS:
            drawn.append(FULL_ROW_HEIGHT_PCT)
            subheading.append(False)
            continue
        is_sub = _is_subheading_row(row)
        subheading.append(is_sub)
        if is_sub and _row_is_blank(row):
            drawn.append(0.0)
        else:
            drawn.append(FULL_ROW_HEIGHT_PCT * SUBHEADING_ROW_HEIGHT_FACTOR
                         if is_sub else FULL_ROW_HEIGHT_PCT)
    return drawn, subheading


def _prepare(content, column_widths, width_emu, height_emu):
    n_cols = len(column_widths)
    w_inches, h_inches = _size_to_inches(width_emu, height_emu)
    left_pad_pct = (LEFT_PAD_INCHES / w_inches) * 100 if w_inches else 0.0

    drawn_row_heights, subheading = _drawn_row_heights(content)

    col_x = [0.0]
    for cw in column_widths:
        col_x.append(col_x[-1] + cw)
    row_y = [0.0]
    for rh in drawn_row_heights:
        row_y.append(row_y[-1] + rh)

    return {
        "content": [list(row) for row in content],
        "col_x": col_x, "row_y": row_y,
        "w_inches": w_inches, "h_inches": h_inches,
        "left_pad_pct": left_pad_pct,
        "n_cols": n_cols, "n_rows": len(content),
        "subheading": subheading, "table_bottom": row_y[-1],
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


def _body_alignment(c, is_subheading):
    if is_subheading:
        return "left"
    return BODY_COLUMN_ALIGNMENTS.get(c, BODY_DEFAULT_ALIGNMENT)


def _body_font_size(c, is_subheading):
    if is_subheading:
        return SUBHEADING_FONT_SIZE
    if c == 0:
        return ID_FONT_SIZE
    return BODY_FONT_SIZE


def _body_font_weight(c, is_subheading):
    if is_subheading:
        return "bold"
    if c == 0:
        return "bold"
    return "normal"


def _aligned_x(alignment, x0, x1, left_pad):
    if alignment == "left":
        return x0 + left_pad
    if alignment == "right":
        return x1 - left_pad
    return (x0 + x1) / 2


def ci_cardtile2(content, column_widths, row_heights, width_emu=5486400, height_emu=3429000, tweaks=""):
    p = _prepare(content, column_widths, width_emu, height_emu)
    fig, ax = _new_axes(p)
    n_rows, n_cols = p["n_rows"], p["n_cols"]
    lp = p["left_pad_pct"]
    full_width = 100.0
    full_height = 100.0
    table_bottom = p["table_bottom"]
    row_y = p["row_y"]
    col_x = p["col_x"]

    chart_cells_raw = {}

    def _record_chart_cell(chart_tag, cx0, cx1, cy0, cy1):
        chart_cells_raw[chart_tag] = (cx0, cx1, cy0, cy1)

    inset_x = _points_to_data_x(LINE_WIDTH / 2, p["w_inches"])
    inset_y = _points_to_data_y(LINE_WIDTH / 2, p["h_inches"])
    rule_x0, rule_x1 = inset_x, full_width - inset_x
    subheading_nudge = _points_to_data_y(
        SUBHEADING_NUDGE_EM * SUBHEADING_FONT_SIZE, p["h_inches"])

    rx = (TABLE_ROUNDING_INCHES / p["w_inches"]) * 100 if p["w_inches"] else 0.0
    ry = (TABLE_ROUNDING_INCHES / p["h_inches"]) * 100 if p["h_inches"] else 0.0
    clip_shape = _rounded_rect_polygon(0, 0, full_width, table_bottom, rx, ry)

    def _add_fill(patch):
        ax.add_patch(patch)
        patch.set_clip_path(clip_shape.get_path(), transform=ax.transData)

    ax.add_patch(mpatches.Rectangle(
        (0, 0), full_width, full_height,
        facecolor="white", edgecolor="none", zorder=0,
    ))

    _add_fill(mpatches.Rectangle(
        (0, 0), full_width, table_bottom,
        facecolor="white", edgecolor="none", zorder=1,
    ))

    if n_rows >= HEADER_ROWS and n_cols > 0:
        header_top = row_y[0]
        header_bottom = row_y[HEADER_ROWS] if HEADER_ROWS < len(row_y) else table_bottom
        header_centre = (header_top + header_bottom) / 2

        _add_fill(mpatches.Rectangle(
            (0, header_top), full_width, header_bottom - header_top,
            facecolor=HEADER_BG, edgecolor="none", zorder=1.5,
        ))

        for c in range(n_cols):
            x0 = col_x[c]
            x1 = col_x[c + 1] if c + 1 < len(col_x) else full_width

            cell_text = _cell_text(p, 0, c)
            chart_tag = _chart_cell_id(cell_text)
            if chart_tag:
                _record_chart_cell(chart_tag, x0, x1, header_top, header_bottom)
                continue

            if c == HEADER_PLAIN_COLUMN_INDEX:
                header_font_size = HEADER_PLAIN_FONT_SIZE
                header_font_weight = "normal"
            else:
                header_font_size = HEADER_BOLD_FONT_SIZE
                header_font_weight = "bold"

            if c in HEADER_LEFT_COLUMN_INDICES:
                ax.text(x0 + lp, header_centre, cell_text, ha="left", va="center",
                        fontsize=header_font_size, fontweight=header_font_weight,
                        color=ACCENT_BLUE, zorder=3)
            else:
                ax.text((x0 + x1) / 2, header_centre, cell_text, ha="center", va="center",
                        fontsize=header_font_size, fontweight=header_font_weight,
                        color=ACCENT_BLUE, zorder=3)

        ax.plot([rule_x0, rule_x1], [header_bottom, header_bottom],
                color=GREY_LINE, linewidth=LINE_WIDTH, zorder=2)

    subheading = p["subheading"]

    for r in range(HEADER_ROWS, n_rows):
        _, _, y0, y1 = _cell_bounds(p, r, 0)
        is_subheading = subheading[r] if r < len(subheading) else True
        is_blank_row = is_subheading and _row_is_blank(p["content"][r])

        if r > HEADER_ROWS and not is_blank_row:
            ax.plot([rule_x0, rule_x1], [y0, y0],
                    color=GREY_LINE, linewidth=LINE_WIDTH, zorder=2)

        if is_subheading:
            if not is_blank_row:
                _add_fill(mpatches.Rectangle(
                    (0, y0), full_width, y1 - y0,
                    facecolor=SUBHEADING_BG, edgecolor="none", zorder=1.6,
                ))
        else:
            band_x0 = col_x[BANDED_COLUMN_INDEX]
            band_x1 = (col_x[BANDED_COLUMN_INDEX + 1]
                       if BANDED_COLUMN_INDEX + 1 < len(col_x) else full_width)
            _add_fill(mpatches.Rectangle(
                (band_x0, y0), band_x1 - band_x0, y1 - y0,
                facecolor=COLUMN1_BG, edgecolor="none", zorder=1.6,
            ))
            for edge in (RULED_COLUMN_INDEX, RULED_COLUMN_INDEX + 1):
                if edge < len(col_x):
                    ax.plot([col_x[edge], col_x[edge]], [y0, y1],
                            color=GREY_LINE, linewidth=LINE_WIDTH, zorder=2)

        text_y = (y0 + y1) / 2 + (subheading_nudge if is_subheading else 0.0)

        for c in range(n_cols):
            cx0, cx1, _, _ = _cell_bounds(p, r, c)
            body_val = _cell_text(p, r, c)
            body_tag = _chart_cell_id(body_val)
            if body_tag:
                _record_chart_cell(body_tag, cx0, cx1, y0, y1)
                continue
            alignment = _body_alignment(c, is_subheading)
            ax.text(_aligned_x(alignment, cx0, cx1, lp), text_y, body_val,
                    ha=alignment, va="center",
                    fontsize=_body_font_size(c, is_subheading),
                    fontweight=_body_font_weight(c, is_subheading),
                    color=BODY_TEXT if c == 0 else GREY_TEXT, zorder=3)

    ax.add_patch(_rounded_rect_polygon(
        inset_x, inset_y, full_width - 2 * inset_x, table_bottom - 2 * inset_y, rx, ry,
        linewidth=LINE_WIDTH, edgecolor=GREY_LINE, facecolor="none", zorder=2.5,
    ))

    chart_cells = _resolve_chart_cells(chart_cells_raw, width_emu, height_emu)
    return _fig_to_bytes(fig), chart_cells
