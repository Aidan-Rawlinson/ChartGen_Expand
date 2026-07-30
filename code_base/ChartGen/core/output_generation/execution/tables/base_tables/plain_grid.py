"""
plain_grid.py
Base Table -- plain_grid. Draws a table as a single image from a resolved
grid of content, with left-aligned first-column text (a small fixed
padding) and a table-wide font size chosen generically so the widest
first-column entry fits with matching padding on both sides.

Standalone artefact, the base_tables equivalent of a Base Chart
(Architecture, Decision 18) -- no imports from ChartGen's own code,
third-party libraries only. Receives already-resolved content (plain
strings; Stat Tags already substituted) and already-parsed column_widths /
row_heights (percent, each expected to sum to ~100) -- no resolution logic
lives here, mirroring how a Base Chart never resolves its own populations.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DPI = 450
NARROWER_DIM_INCHES = 7.5

# Font-size search bounds for the "shrink to fit column 1" behaviour.
MAX_FONT_SIZE = 12
MIN_FONT_SIZE = 4
FONT_STEP = 0.5

# Fixed physical left-hand padding for column 1 text. The font size is then
# chosen so the widest column-1 string leaves this same amount of clear
# space on the right as well.
LEFT_PAD_INCHES = 0.08


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


def plain_grid(content: list, column_widths: list, row_heights: list,
               width=80, height=50, tweaks=""):
    """
    content       -- list[list[str]], already-resolved cell text, N rows x M cols
    column_widths -- list[float], % of table width, length M
    row_heights   -- list[float], % of table height, length N
    """
    n_cols = len(column_widths)

    w_inches, h_inches = _size_to_inches(width, height)

    # Convert the fixed physical left padding into the 0-100
    # percent-of-table-width coordinate system used for plotting.
    left_pad_pct = (LEFT_PAD_INCHES / w_inches) * 100 if w_inches else 0.0

    col0_width_pct = column_widths[0] if column_widths else 0.0
    col0_width_inches = (col0_width_pct / 100.0) * w_inches
    available_inches = col0_width_inches - (2 * LEFT_PAD_INCHES)

    # Font size is fit against every column-1 string that will actually be drawn.
    col0_texts = [row[0] if row else "" for row in content]
    font_size = _fit_font_size(col0_texts, available_inches, DPI)

    fig, ax = plt.subplots(figsize=(w_inches, h_inches))
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

    for r in range(n_rows):
        for c in range(n_cols):
            x0 = col_x[c]
            x1 = col_x[c + 1] if c + 1 < len(col_x) else 100.0
            y0 = row_y[r]
            y1 = row_y[r + 1] if r + 1 < len(row_y) else 100.0
            rect = mpatches.Rectangle(
                (x0, y0), x1 - x0, y1 - y0,
                facecolor="white", edgecolor="black", linewidth=0.75,
            )
            ax.add_patch(rect)

            row_data = content[r]
            cell_text = row_data[c] if c < len(row_data) else ""

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

    fig.tight_layout(pad=0)
    return _fig_to_bytes(fig)
