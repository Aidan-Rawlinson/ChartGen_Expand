"""
plain_grid.py
Base Table -- plain_grid. Draws a table as a single image from a resolved
grid of content, with left-aligned first-column text (a small fixed
padding) and a table-wide font size chosen generically so the widest
first-column entry fits with matching padding on both sides.

Standalone artefact, the base_tables equivalent of a Base Chart
(Architecture, Decision 18) -- no imports from ChartGen's own code,
third-party libraries only. Receives already-resolved content (plain
strings; Stat Tags already substituted, chart-component cell markers
"{Cn}" left as literal text -- Decisions.md) and already-parsed
column_widths / row_heights (percent, each expected to sum to ~100) -- no
resolution logic lives here, mirroring how a Base Chart never resolves its
own populations.

Returns (image_bytes, chart_cells) -- the table_inputs return contract
(Decisions.md): chart_cells is {tag: {"x", "y", "width", "height"}} in
EMU, one entry per "{Cn}" cell this function actually drew space for
(skipped entirely, not drawn as text). A style with no chart-cell support
would simply never populate it -- returning {} is always valid.
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

DPI = 300
EMU_PER_INCH = 914400

# PowerPoint SVG-text-compression workaround -- see line_ci_full's own
# TEXT_SCALE comment for the full reasoning. Must match the system
# layer's own CHART_RENDER_SCALE (insert_table.py) exactly.
#
# Applied to every constant below, not just a fontsize literal: the
# font-size search (_fit_font_size) is bounded by MAX_FONT_SIZE, and its
# available width is col0_width_inches minus LEFT_PAD_INCHES on each
# side -- both fixed *physical* quantities. Called at TEXT_SCALE times
# the real width_emu/height_emu, w_inches grows by the same factor, but
# an unscaled LEFT_PAD_INCHES/MAX_FONT_SIZE would leave the search
# finding a font size capped at the same absolute 12pt regardless of how
# much bigger the canvas got -- defeating the whole point (the chosen
# font would come out proportionally tiny once shrunk back to real
# size). Scaling every physical constant here by the same factor keeps
# the algorithm's behaviour proportionally identical to the real size,
# just computed on a bigger canvas.
TEXT_SCALE = 5

# Font-size search bounds for the "shrink to fit column 1" behaviour.
MAX_FONT_SIZE = 12 * TEXT_SCALE
MIN_FONT_SIZE = 4 * TEXT_SCALE
FONT_STEP = 0.5 * TEXT_SCALE

# Fixed physical left-hand padding for column 1 text. The font size is then
# chosen so the widest column-1 string leaves this same amount of clear
# space on the right as well.
LEFT_PAD_INCHES = 0.08 * TEXT_SCALE


def _size_to_inches(width_emu, height_emu):
    return width_emu / EMU_PER_INCH, height_emu / EMU_PER_INCH


def _chart_cell_id(cell_text):
    """
    None if `cell_text` isn't a chart-component cell marker; otherwise the
    Chart Store id it names (e.g. "C3"). A marker is exactly "{" + id + "}"
    with nothing else in the cell -- string slicing only, no regex, so this
    stays within the same allowed-builtins set a Custom Table is permitted
    (no need to add "re" to ALLOWED_IMPORTS for this). Chart Store ids
    always start with "C" (Architecture, Decision 28's own id prefix,
    distinguishing them from a Stat Tag's "T" prefix) -- checked here so an
    ordinary "{note}"-style bracketed comment a person typed isn't
    mistaken for one.
    """
    t = (cell_text or "").strip()
    if len(t) > 2 and t.startswith("{") and t.endswith("}"):
        inner = t[1:-1]
        if inner.startswith("C"):
            return inner
    return None


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    # No bbox_inches="tight" -- that crops the saved SVG to the actual ink
    # extent of whatever got drawn, which is content-dependent and not
    # symmetric. This function draws nothing outside the axes (no bleed,
    # no clip_on=False -- a style that deliberately draws overflowing
    # decoration, like table_cardtile's own drop shadows, needs a
    # different, more careful treatment of this), so dropping the crop
    # here means the 0-100 data-coordinate system this function plots in
    # maps exactly onto the saved canvas -- required for a chart-component
    # cell's own reported EMU rectangle (computed as a fraction of
    # width_emu/height_emu) to land exactly where the cell border is
    # actually drawn once inserted, rather than drifting by whatever
    # margin a content-dependent crop happened to trim.
    fig.savefig(buf, format="svg", facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def _text_width_inches(text, fontsize, dpi):
    """Measures the rendered width of a string at a given font size, in
    inches, using a disposable throwaway figure at the target DPI."""
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
    """Measures the rendered height of a string at a given font size, in
    inches, using a disposable throwaway figure at the target DPI. A
    string with embedded newlines (resolve.py's own "<br>" conversion)
    renders as stacked lines -- matplotlib does this natively -- so this
    picks up the full multi-line height, not just one line's."""
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
    """Largest font size, within bounds, at which every non-empty string
    in `texts` fits inside `available_width_inches`. Generic over the
    actual text content -- no specific values assumed."""
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
    """
    A multi-line cell (resolve.py's "<br>" -> real newline conversion)
    renders as stacked lines, which _fit_font_size never considers -- it
    only ever measures width. This is a second, separate pass: starting
    from the width-fit size already chosen, shrink further (never grow
    back past it) until every cell containing a newline renders, at the
    returned size, within its own row's full height -- otherwise the
    overflow would sit underneath the next row's own white rectangle,
    which is drawn afterwards and would silently cover it.
    A chart-component cell is skipped -- it isn't drawn as text at all.
    """
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
    """
    content       -- list[list[str]], already-resolved cell text, N rows x M cols
    column_widths -- list[float], % of table width, length M
    row_heights   -- list[float], % of table height, length N
    """
    n_cols = len(column_widths)

    w_inches, h_inches = _size_to_inches(width_emu, height_emu)

    # Convert the fixed physical left padding into the 0-100
    # percent-of-table-width coordinate system used for plotting.
    left_pad_pct = (LEFT_PAD_INCHES / w_inches) * 100 if w_inches else 0.0

    col0_width_pct = column_widths[0] if column_widths else 0.0
    col0_width_inches = (col0_width_pct / 100.0) * w_inches
    available_inches = col0_width_inches - (2 * LEFT_PAD_INCHES)

    # Font size is fit against every column-1 string that will actually be
    # drawn -- a chart-component cell isn't drawn as text at all, so it's
    # excluded here rather than measured as if it were a literal string.
    col0_texts = [
        row[0] for row in content
        if row and not _chart_cell_id(row[0])
    ]
    font_size = _fit_font_size(col0_texts, available_inches, DPI)
    font_size = _shrink_for_multiline_height(font_size, content, row_heights, h_inches, DPI)

    fig = plt.figure(figsize=(w_inches, h_inches))
    # The axes fill the entire figure canvas exactly ([0,0,1,1] in
    # figure-fraction coordinates) -- no tight_layout heuristic, no
    # subplot-spacing guesswork. This guarantees the 0-100 data-coordinate
    # system set below maps precisely onto the full physical canvas
    # (w_inches x h_inches), which is what makes a chart-component cell's
    # reported EMU rectangle land exactly where its cell border is
    # actually drawn, rather than an approximation.
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.invert_yaxis()
    ax.axis("off")

    # Cumulative offsets, in percent-of-table units -- row 0 / col 0 at the
    # top-left, matching the grid's own authoring layout.
    col_x = [0.0]
    for cw in column_widths:
        col_x.append(col_x[-1] + cw)
    row_y = [0.0]
    for rh in row_heights:
        row_y.append(row_y[-1] + rh)

    n_rows = len(content)

    # Chart-component cells this render found -- {tag: {x, y, width,
    # height}}, all four in EMU (the same unit width_emu/height_emu are
    # already in), each rectangle exactly the cell it names, no rotation
    # or other transform (Decisions.md -- resizing/placement only, first
    # pass). A caller inserts the named Chart Store entry's own chart at
    # this rectangle, layered on top of this table's own picture, never
    # composited into the SVG itself (Decisions.md).
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
                # Left-aligned with a small padding; font size above is
                # chosen so the widest entry here leaves a matching gap
                # on the right as well.
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
