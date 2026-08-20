"""
ci_cardtile.py
Base Table -- a tailored variant of table_cardtile.py for CI-style
tables: a two-row header (rows 0 and 1 of content/row_heights are BOTH
header rows now, not just row 0), and body cards (index 2 onward) that
draw nothing at all -- no card, no shadow, no text -- when every cell in
that row is blank, so a workfile can use a fixed row count and leave
trailing rows empty for consistent sizing across tables with different
real row counts, without a visible empty card where the extra rows sit.
The row's own height is still reserved in the layout either way -- only
what's drawn changes, never the sizing.

Two-row header design (deliberately tailored, not generic -- this table
type always has this exact shape):
  - One single rounded background block spans the whole two-row header
    area, full width -- same rounding radius as the body cards
    (CARD_ROUNDING_INCHES) -- rather than a flat, sharp-cornered
    rectangle, which didn't read as a cohesive element against the
    rounded cards below it. It also carries the same drop-shadow
    treatment as a body card -- a second, offset copy of the same shape
    behind it (border + secondary shape of matching dimensions, the same
    technique the body cards already use) -- using the exact same
    offset_x/offset_y a body card's own shadow uses (derived from the
    first body row's own height), not a fraction re-derived from the
    header's own much taller (two-row) height, which produced a visibly
    bigger shadow gap than any body card's. The header block itself is
    shrunk slightly off its own bottom edge by exactly that same offset,
    to make room for the shadow within the header's existing allocated
    height rather than letting it push into the first body row -- all
    header text is lifted up by half that shrink to stay correctly
    centred within the now-slightly-shorter block.
  - Every column except the final two gets ONE header label spanning both
    header rows' combined height, showing row 0's own resolved text,
    bold accent-blue, vertically centred -- col 0 left-aligned, every
    other column centred (not right-aligned -- unlike the body rows,
    which stay right-aligned to line up with their own numeric values,
    a right-aligned heading sitting alone above a column read
    awkwardly). Row 1's content for these columns is never read.
  - The final two columns' row 0 is ONE label merged horizontally across
    both of them, showing the fixed text "Benchmark" -- not read from
    resolved content -- sitting in the upper half of the shared header
    block.
  - The final two columns' row 1 shows fixed text -- "Target" and
    "Met(?)" -- bold accent-blue, centred, in the lower half of the
    shared header block, regardless of whatever's actually in content[1]
    for those columns; these, and "Benchmark", are a fixed design element
    of this table type, not read from resolved content.
  - Header text sourced from row 0 (the leading columns' own labels, and
    "Benchmark") is HEADER_FONT_BOOST points larger than the row-1
    sub-headings ("Target"/"Met(?)") -- a small visual hierarchy between
    the primary heading and its sub-heading, not a uniform header size.
  - The two header rows are drawn HEADER_ROW_HEIGHT_REDUCTION shorter
    than their own authored row_heights -- a rendering-only adjustment
    (_adjusted_row_heights, applied once in _prepare); the freed height
    is redistributed into the body rows so the table still fills the
    same canvas, nothing left blank. The stored/authored heights
    themselves are never touched.

table_cardtile.py's own header-position "nudge" (balancing the header
text's baseline against row 1's own text height) assumed a single header
row immediately followed by body row 1 -- with the header now spanning
two full rows of its own and body cards starting at index 2, that nudge
no longer applies; header text is simply vertically centred in the full
two-row header block instead.

Standalone artefact, the base_tables equivalent of a Base Chart
(Architecture, Decision 18) -- no imports from ChartGen's own code,
third-party libraries only. Receives already-resolved content and
already-parsed column_widths / row_heights -- no resolution logic lives
here.

Returns (image_bytes, chart_cells) -- the table_inputs return contract
(Decisions.md).
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

# Calibri -- ChartGen's standard chart/table font. SVG text is kept as
# real text, not glyph outlines -- see line_ci_full's own comment for
# the full reasoning.
matplotlib.rcParams["font.family"] = "Calibri"
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

DPI = 300
EMU_PER_INCH = 914400

# PowerPoint SVG-text-compression workaround -- see line_ci_full's own
# TEXT_SCALE comment for the full reasoning. Must match the system
# layer's own CHART_RENDER_SCALE (insert_table.py) exactly. Applied to
# every fixed physical-inch/absolute-point constant below (font bounds,
# padding, card rounding, border width, save padding, header font
# boost) -- see plain_grid.py's own comment for why an unscaled
# font-size search bound or padding constant would defeat the whole
# mechanism once called at an inflated canvas size.
TEXT_SCALE = 5

MAX_FONT_SIZE = 12 * TEXT_SCALE
MIN_FONT_SIZE = 4 * TEXT_SCALE
FONT_STEP = 0.5 * TEXT_SCALE
LEFT_PAD_INCHES = 0.08 * TEXT_SCALE

ACCENT_BLUE = "#1265A5"  # a step darker than the previous #1887DC (itself sparkline1's own MEDIAN_LINE_COL derivation) -- HLS lightness -0.12 further
GREY_LINE = "#C9D2DA"
GREY_TEXT = "#5B6770"
HEADER_BG = "#FCFEFF"  # a third of the previous tint's intensity (~2% of the base blue #7CB9E8 blended toward white, was ~6%) -- paler still, per request; now the gradient's own END colour (right side) -- see HEADER_BG_GRADIENT_START
HEADER_BG_GRADIENT_START = "#DEEEF9"  # a decent step darker than the previous #F3F9FD (~9% tint) -- now a 25% tint of the base blue #7CB9E8, fading to HEADER_BG on the right

CARD_ROUNDING_INCHES = 0.06 * TEXT_SCALE
BORDER_WIDTH = 0.375 * TEXT_SCALE
SHADOW_OFFSET_FRACTION = 0.065
SAVE_PAD_INCHES = 0.03 * TEXT_SCALE
CARD_HEIGHT_FRACTION = 0.8

HEADER_ROWS = 2
MERGED_HEADER_LABEL = "Benchmark"  # fixed label spanning the final two columns' row 0
SUB_HEADINGS = ["Target", "Met(?)"]  # fixed text for the final two columns' row 1
HEADER_FONT_BOOST = 2 * TEXT_SCALE  # points added to header text sourced from row 0 (leading columns + "Benchmark") -- not the row-1 sub-headings
CENTRED_BODY_COLUMN_INDEX = 3  # the fourth column (0-indexed) -- centred instead of right-aligned, unlike every other body column
HEADER_ROW_HEIGHT_REDUCTION = 1 / 3  # rendering-only: the two header rows are drawn a third shorter than authored, freed height redistributed into the body rows


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
    """Same crop-correction as table_cardtile.py's own version -- see
    that file for the full reasoning; unchanged here."""
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
    """Same purpose as table_cardtile.py's own version, restricted to body
    rows -- the header's two rows are a fixed design element here, not
    arbitrary multi-line content. Every body row uses CARD_HEIGHT_FRACTION
    of its own row height, matching the card's own inset."""
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
    """
    Rendering-only adjustment, applied after row_heights is received --
    the stored/authored values (whatever's actually saved for this table)
    are never touched, only what gets drawn. Shrinks the header rows'
    own combined height by `reduction` (a third, by default) and
    redistributes exactly that freed height across the body rows, in
    proportion to each one's own existing share of the body's total --
    so the table still fills the same width_emu x height_emu canvas, with
    nothing left blank at the bottom.
    """
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

    # The exact same offset_x/offset_y a body card's own shadow uses --
    # not a fraction re-derived from the header's own (much taller,
    # two-row) height, which produced a visibly bigger shadow gap than
    # every body card's. Based on the first body row's own height, same
    # as any body card's own offset_y = card_h * SHADOW_OFFSET_FRACTION
    # calculation below -- reused as-is for the header, on the assumption
    # (true for this table type) that body rows share a common height.
    row_y_all = p["row_y"]
    if n_rows > HEADER_ROWS and HEADER_ROWS + 1 < len(row_y_all):
        ref_row_h = row_y_all[HEADER_ROWS + 1] - row_y_all[HEADER_ROWS]
    else:
        ref_row_h = row_y_all[-1] - row_y_all[0] if len(row_y_all) > 1 else 0.0
    ref_card_h = ref_row_h * CARD_HEIGHT_FRACTION
    shadow_offset_y = ref_card_h * SHADOW_OFFSET_FRACTION
    shadow_offset_x = shadow_offset_y * (p["h_inches"] / p["w_inches"]) if p["w_inches"] else shadow_offset_y

    # -- Header: rows 0 and 1 combined --
    if n_rows >= HEADER_ROWS and n_cols > 0:
        row_y = p["row_y"]
        col_x = p["col_x"]
        header_top = row_y[0]
        header_bottom_full = row_y[HEADER_ROWS] if HEADER_ROWS < len(row_y) else 100.0
        header_full_h = header_bottom_full - header_top

        # Shrink the block off its own bottom edge by exactly
        # shadow_offset_y, to leave room for the shadow within the
        # header's existing allocated height, rather than letting it push
        # into the first body row. Lift is half that shrink, so all
        # header text stays centred within the resulting (slightly
        # shorter) block rather than drifting toward its new, higher
        # bottom edge.
        header_offset_y = shadow_offset_y
        header_offset_x = shadow_offset_x
        lift = header_offset_y / 2
        header_block_h = header_full_h - header_offset_y
        header_bottom = header_top + header_block_h  # the block's own new bottom edge

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

        # Gradient fill (darker left, fading to HEADER_BG on the right) --
        # same technique sparkline1.py uses for its own median fill: an
        # imshow image spanning the block's own rectangle, clipped to the
        # block's rounded-corner path rather than a flat facecolor. The
        # block's own border is drawn as a separate, unfilled polygon on
        # top, so the gradient never covers the border stroke.
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

    # -- Body cards: index HEADER_ROWS onward --
    for r in range(HEADER_ROWS, n_rows):
        row_data = p["content"][r]
        if _row_is_blank(row_data, n_cols):
            # Nothing at all -- no card, no shadow, no text. row_y (built
            # from the full row_heights list) already reserves this row's
            # own space regardless, so every other row's position and the
            # table's overall size are unaffected by how many rows turn
            # out blank.
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
