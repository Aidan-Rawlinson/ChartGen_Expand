"""
resolve.py
Resolves an Output Table's grid into plain values ready for a base_table
renderer: parsed column widths / row heights, and a content grid with every
"[tag]" Stat Tag resolved to its current value for the reporting unit --
the same token map update_text uses (build_stat_tag_tokens,
core.output_generation.execution.text.text_engine), not duplicated here.
Literal text passes straight through.

Chart-component cells ("{n}") are recognised by the grid's own grammar
(grid_store.py) but parked this session -- not resolved or rendered; a
cell holding one is left as its literal text, same as anything else
unresolved.
"""

from core.output_generation.execution.tables.grid_store import (
    get_column_widths, get_row_heights, get_content_grid,
)
from core.output_generation.execution.text.text_engine import build_stat_tag_tokens


def resolve_output_table(grid_rows: list, workfile_state, full_unit_set: dict) -> dict:
    """
    Returns {"column_widths": [...], "row_heights": [...], "content": [[...]]}.
    content is a plain list[list[str]], every resolvable "[tag]" replaced,
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
            resolved_row.append(resolved)
        resolved_content.append(resolved_row)

    return {
        "column_widths": column_widths,
        "row_heights": row_heights,
        "content": resolved_content,
    }
