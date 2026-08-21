"""
grid_store.py
Output Table grid storage shape and mechanics.

An Output Table's grid is a single flat, spreadsheet-shaped artefact -- an
(N+1) x (M+1) grid for an N-row x M-column Output Table, stored as
workfile_config/output_tables/{table_id}.csv (WorkfileState.output_tables,
keyed by table_id) -- mirroring the population tables' own "no fixed
schema, each written from its own rows' keys" convention
(chartgen.workfile.state.workfile_file).

Layout (0-indexed internally; 1-indexed in user-facing language):
  - Row 0, col 0  ("corner")   -- the table's own table_id. Display only,
                                   never read back for anything.
  - Row 0, cols 1..M           -- column widths, % of total table width,
                                   2 decimal places.
  - Rows 1..N, col 0           -- row heights, % of total table height,
                                   2 decimal places.
  - Rows 1..N, cols 1..M       -- content cells: constant text, a Stat
                                   Tag id ("[T3]"), or a Chart Store
                                   chart-component marker ("{C3}") --
                                   recognised and acted on by the Base
                                   Table function itself, not resolved
                                   here (Decision 28).

Columns are named c0..cM (generic, matching the no-fixed-schema convention
population tables already use) rather than anything content-specific.
col_key() is the single source of truth for that naming, reused by
grid_xlsx.py's own Excel round-trip so the two never drift apart.
"""

from chartgen.shared.infrastructure.id_generation import next_id

OUTPUT_TABLE_COUNTER_KEY = "next_table_id"

# Every Output Table starts at this size, whether created via a template's
# [Table] yellow box or the Output Tables tab's own "+ New Output Table"
# form -- no user-configurable Rows/Columns at creation time either way
# (Decisions.md). Resize afterwards via the existing Resize control.
DEFAULT_TABLE_ROWS = 7
DEFAULT_TABLE_COLUMNS = 4

# Tolerance for the column-widths-sum-to-100% / row-heights-sum-to-100%
# validation check -- rounding two-decimal percentages across an arbitrary
# column/row count will rarely land on exactly 100.00.
SIZE_SUM_TOLERANCE = 0.5


def next_table_id(settings: dict) -> str:
    return next_id(settings, OUTPUT_TABLE_COUNTER_KEY)


def col_key(c: int) -> str:
    """Public: the c0..cM column-name convention this module and grid_xlsx.py both use."""
    return f"c{c}"


def new_grid(table_id: str, n_rows: int, n_cols: int) -> list:
    """
    Build a fresh (n_rows+1) x (n_cols+1) grid: corner cell holds table_id,
    row 0 (cols 1..n_cols) defaults to equal column widths (100/n_cols,
    2dp), col 0 (rows 1..n_rows) defaults to equal row heights (100/n_rows,
    2dp), content cells blank. Rounding drift against an exact 100.00 total
    is accepted, not corrected (Decisions.md).
    """
    col_width = round(100.0 / n_cols, 2) if n_cols else 0.0
    row_height = round(100.0 / n_rows, 2) if n_rows else 0.0

    grid = []

    header_row = {col_key(0): table_id}
    for c in range(1, n_cols + 1):
        header_row[col_key(c)] = f"{col_width:.2f}"
    grid.append(header_row)

    for r in range(1, n_rows + 1):
        row = {col_key(0): f"{row_height:.2f}"}
        for c in range(1, n_cols + 1):
            row[col_key(c)] = ""
        grid.append(row)

    return grid


def grid_dimensions(grid_rows: list) -> tuple:
    """Return (n_rows, n_cols) -- content dimensions, excluding the header row/column."""
    n_rows = max(0, len(grid_rows) - 1)
    n_cols = max(0, len(grid_rows[0]) - 1) if grid_rows else 0
    return n_rows, n_cols


def get_table_id(grid_rows: list) -> str:
    if not grid_rows:
        return ""
    return str(grid_rows[0].get(col_key(0), ""))


def get_column_widths(grid_rows: list) -> list:
    """Row 0, cols 1..M, as floats. Unparsable cells resolve to 0.0."""
    if not grid_rows:
        return []
    _, n_cols = grid_dimensions(grid_rows)
    header = grid_rows[0]
    widths = []
    for c in range(1, n_cols + 1):
        try:
            widths.append(float(header.get(col_key(c), "0") or "0"))
        except (TypeError, ValueError):
            widths.append(0.0)
    return widths


def get_row_heights(grid_rows: list) -> list:
    """Col 0, rows 1..N, as floats. Unparsable cells resolve to 0.0."""
    if not grid_rows:
        return []
    heights = []
    for row in grid_rows[1:]:
        try:
            heights.append(float(row.get(col_key(0), "0") or "0"))
        except (TypeError, ValueError):
            heights.append(0.0)
    return heights


def get_content_grid(grid_rows: list) -> list:
    """
    Rows 1..N x cols 1..M, as a plain list[list[str]] of raw cell text --
    unresolved: literal text, "[tag]", or "{component}" markers exactly as
    typed. Resolution (Stat Tags today; chart components once unparked)
    happens in resolve.py, not here.
    """
    if not grid_rows:
        return []
    _, n_cols = grid_dimensions(grid_rows)
    content = []
    for row in grid_rows[1:]:
        content.append([str(row.get(col_key(c), "") or "") for c in range(1, n_cols + 1)])
    return content


def set_content_cell(grid_rows: list, r: int, c: int, value: str):
    """r, c are 1-based content-grid coordinates (1..N, 1..M)."""
    grid_rows[r][col_key(c)] = value


def validate_grid(grid_rows: list) -> list:
    """
    Check column widths (row 0) sum to 100% +/- SIZE_SUM_TOLERANCE, and row
    heights (col 0) sum to 100% +/- SIZE_SUM_TOLERANCE, independently.
    Returns a list of warning strings -- empty list means valid. Advisory
    only: out-of-tolerance values are flagged, never auto-corrected
    (Decisions.md).
    """
    warnings = []
    widths = get_column_widths(grid_rows)
    heights = get_row_heights(grid_rows)

    width_total = sum(widths)
    if abs(width_total - 100.0) > SIZE_SUM_TOLERANCE:
        warnings.append(
            f"Column widths sum to {width_total:.2f}%, not 100% "
            f"(tolerance +/-{SIZE_SUM_TOLERANCE}%)."
        )
    height_total = sum(heights)
    if abs(height_total - 100.0) > SIZE_SUM_TOLERANCE:
        warnings.append(
            f"Row heights sum to {height_total:.2f}%, not 100% "
            f"(tolerance +/-{SIZE_SUM_TOLERANCE}%)."
        )
    return warnings


def resize_grid(grid_rows: list, new_n_rows: int, new_n_cols: int, table_id: str) -> list:
    """
    Resize a grid to new_n_rows x new_n_cols, preserving existing content,
    widths, and heights wherever the old and new coordinates overlap. A row
    or column introduced by growing the grid gets an even share (100/count,
    2dp -- the same default new_grid uses), computed independently of the
    survivors rather than recalculated against them, so growing the grid
    never silently rewrites sizes already authored elsewhere on it.
    """
    old_widths = get_column_widths(grid_rows)
    old_heights = get_row_heights(grid_rows)
    old_content = get_content_grid(grid_rows)

    default_w = round(100.0 / new_n_cols, 2) if new_n_cols else 0.0
    default_h = round(100.0 / new_n_rows, 2) if new_n_rows else 0.0

    new_widths = [
        old_widths[c] if c < len(old_widths) else default_w
        for c in range(new_n_cols)
    ]
    new_heights = [
        old_heights[r] if r < len(old_heights) else default_h
        for r in range(new_n_rows)
    ]

    grid = []
    header_row = {col_key(0): table_id}
    for c in range(1, new_n_cols + 1):
        header_row[col_key(c)] = f"{new_widths[c - 1]:.2f}"
    grid.append(header_row)

    for r in range(1, new_n_rows + 1):
        row = {col_key(0): f"{new_heights[r - 1]:.2f}"}
        for c in range(1, new_n_cols + 1):
            old_val = ""
            if r - 1 < len(old_content) and c - 1 < len(old_content[r - 1]):
                old_val = old_content[r - 1][c - 1]
            row[col_key(c)] = old_val
        grid.append(row)

    return grid
