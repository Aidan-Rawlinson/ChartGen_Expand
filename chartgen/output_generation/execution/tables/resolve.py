"""
resolve.py
Resolves an Output Table's grid into plain values ready for a Base Table:
parsed column widths and row heights, and a content grid with every Stat Tag
resolved to its current value for the reporting unit. Uses the same token
map update_text builds, not a duplicate. Literal text passes through.

The one shared place both the final report and the Preview resolve content
through, so two conventions are handled here and nowhere else.

Chart-component cells ("{Cn}") are left untouched, like any other literal.
The Base Table function recognises them itself and reports back the
rectangle it reserved, rather than drawing them as text.

A typed "<br>", "<br/>" or "<br />", case-insensitive, becomes a real
newline, so a Base Table only ever handles an actual newline character.
Matplotlib renders an embedded newline as stacked lines natively.
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
