"""
resolve.py
Resolves an Output Table's grid into plain values ready for a base_table
renderer: parsed column widths / row heights, and a content grid with every
"[tag]" Stat Tag resolved to its current value for the reporting unit --
the same token map update_text uses (build_stat_tag_tokens,
chartgen.output_generation.execution.text.text_engine), not duplicated here.
Literal text passes straight through.

Chart-component cells ("{Cn}") are recognised by the grid's own grammar
(grid_store.py) but left untouched here, exactly like any other
unresolved literal text -- a Base Table function itself recognises and
acts on them (Decision 28), reporting back the cell rectangle it reserved
for each one rather than drawing it as text. Text resolution (this
module) and chart-cell resolution (inside the Base Table function) are
deliberately two separate steps against the same content grid.

Line breaks: a typed "<br>" (also "<br/>" and "<br />", case-insensitive)
is converted to a real newline here -- the one shared place both the
final report (insert_table.py) and the Preview (output_tables_tab.py) both
resolve content through, so a Base Table function only ever needs to
handle an actual "\\n" character, never the typed convention itself.
Matplotlib's own Text renders an embedded "\\n" as stacked lines natively;
no Base Table function needs to know "<br>" exists.
"""

import re

from chartgen.output_generation.execution.tables.grid_store import (
    get_column_widths, get_row_heights, get_content_grid,
)
from chartgen.output_generation.execution.text.text_engine import build_stat_tag_tokens

_BR_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)


def resolve_output_table(grid_rows: list, workfile_state, full_unit_set: dict) -> dict:
    """
    Returns {"column_widths": [...], "row_heights": [...], "content": [[...]]}.
    content is a plain list[list[str]], every resolvable "[tag]" replaced
    and every "<br>"-style line break converted to a real newline,
    everything else left exactly as typed.
    """
    column_widths = get_column_widths(grid_rows)
    row_heights = get_row_heights(grid_rows)
    raw_content = get_content_grid(grid_rows)

    tokens = build_stat_tag_tokens(workfile_state, full_unit_set) if workfile_state is not None else {}

    resolved_content = []
    for row in raw_content:
        resolved_row = []
        for cell in row:
            resolved = cell
            for token, value in tokens.items():
                if token in resolved:
                    resolved = resolved.replace(token, value)
            resolved = _BR_PATTERN.sub("\n", resolved)
            resolved_row.append(resolved)
        resolved_content.append(resolved_row)

    return {
        "column_widths": column_widths,
        "row_heights": row_heights,
        "content": resolved_content,
    }
