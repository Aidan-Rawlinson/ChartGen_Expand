"""
bundle.py
Builds the Custom Tables download bundle -- a single, self-contained text
document combining the shared table_inputs contract (contract.py), the
current table's own source code, and its live resolved grid for the table
actually on screen. Designed to be dropped whole into a fresh chat with no
other context: everything needed to reason about and modify the table is
in this one document.
"""

import inspect
import json

from core.output_generation.execution.tables.base_tables import TABLE_REGISTRY
from core.output_generation.execution.tables.custom_tables.contract import build_static_sections


def _get_table_source(table_type_ref: str, custom_table_code: dict) -> str:
    """
    Built-in: read the whole module the function lives in, not just the
    function itself -- mirrors the chart bundle's own reasoning (a Base
    Table may carry its own inlined helpers/constants; inspect.getsource
    on the function object alone would silently drop everything it
    depends on). Custom: stored source text is already the complete file
    as pasted in.
    """
    if table_type_ref in TABLE_REGISTRY:
        module = inspect.getmodule(TABLE_REGISTRY[table_type_ref])
        return inspect.getsource(module)
    if custom_table_code and table_type_ref in custom_table_code:
        return custom_table_code[table_type_ref]
    raise ValueError(f"Unknown table_type_ref: {table_type_ref}")


def _grid_to_json(content: list, column_widths: list, row_heights: list) -> str:
    """Serialise the live resolved grid passed to this table, as-is, to JSON text."""
    return json.dumps(
        {"content": content, "column_widths": column_widths, "row_heights": row_heights},
        indent=2, default=str,
    )


def build_bundle(table_type_ref: str, content: list, column_widths: list, row_heights: list,
                 width: int, height: int, tweaks: str, custom_table_code: dict = None) -> str:
    """
    Build the complete Custom Tables download document for one table, as
    currently configured and rendering on screen.
    """
    source = _get_table_source(table_type_ref, custom_table_code)
    live_data = _grid_to_json(content, column_widths, row_heights)

    return f"""\
{build_static_sections()}

## Current code for this table ("{table_type_ref}")

This is the complete file, exactly as it will run -- every import,
constant, and helper function, together with the entry-point function
itself. There is nothing outside what's shown below.

```python
{source}
```

## Live data for this table, right now

This is the actual content / column_widths / row_heights this table is
currently being called with -- the same data you would need to reason
about to check any change you make.

width = {width}
height = {height}
tweaks = "{tweaks}"

```json
{live_data}
```
"""
