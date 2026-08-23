"""
bundle.py
Builds the Custom Tables download bundle -- a single, self-contained text
document combining the shared table_inputs contract (contract.py), the
current table's own source code, and its live resolved grid for the table
actually on screen. Designed to be dropped whole into a fresh chat with no
other context: everything needed to reason about and modify the table is
in this one document.

Optionally (include_charts=True) also bundles full detail for every
Chart Store entry referenced by a "{Cn}" marker anywhere in the grid --
that entry's own settings, its complete rendering source, and its live
population_layers -- so a table with chart-component cells can be
rebuilt in full from this one document too, with no separate Custom
Charts bundle needed alongside it. Off by default: most table edits
don't touch what's inside an embedded chart, and resolving each one's
live data has a real cost (cache load, cut resolution) worth skipping
when not wanted.
"""

import dataclasses
import inspect
import json
import re

from chartgen.output_generation.execution.charts.base_charts import CHART_REGISTRY
from chartgen.output_generation.execution.charts.chart_store import resolve_chart_store_population_layers
from chartgen.output_generation.execution.tables.base_tables import TABLE_REGISTRY
from chartgen.output_generation.execution.tables.custom_tables.contract import build_static_sections

# Same marker grammar every Base Table's own _chart_cell_id recognises
# independently: "{" + id + "}", id starting with "C". Written once here
# because bundle.py is system code, not a Base Table.
#
# Must stay exactly as permissive as _chart_cell_id's real check:
# inner.startswith("C"), nothing more. Requiring [0-9a-z]+ after the "C"
# excludes hand-typed ids such as "{CH1}" and "{CV1}", which
# _chart_cell_id treats as valid.
_CHART_MARKER_RE = re.compile(r"^\{(C.*)\}$")


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


def _get_chart_source(base_chart_name: str, custom_chart_code: dict) -> str:
    """
    Same purpose as custom_charts/bundle.py's own _get_chart_source, kept as
    its own copy because the two rendering domains are independent.
    """
    if base_chart_name in CHART_REGISTRY:
        module = inspect.getmodule(CHART_REGISTRY[base_chart_name])
        return inspect.getsource(module)
    if custom_chart_code and base_chart_name in custom_chart_code:
        return custom_chart_code[base_chart_name]
    raise ValueError(f"Unknown base_chart_name: {base_chart_name}")


def _grid_to_json(content: list, column_widths: list, row_heights: list) -> str:
    """Serialise the live resolved grid passed to this table, as-is, to JSON text."""
    return json.dumps(
        {"content": content, "column_widths": column_widths, "row_heights": row_heights},
        indent=2, default=str,
    )


def _layers_to_json(population_layers: list) -> str:
    """Same as custom_charts/bundle.py's own _layers_to_json."""
    return json.dumps([dataclasses.asdict(layer) for layer in population_layers], indent=2, default=str)


def _referenced_chart_store_ids(content: list) -> list:
    """Every distinct Chart Store id referenced by a "{Cn}" marker anywhere
    in `content`, in first-seen order. A cell that isn't exactly one
    marker (any other text, including a marker plus anything else) is not
    matched -- the same "whole cell, nothing else" rule every Base Table's
    own marker check applies."""
    seen = []
    for row in content:
        for cell in row:
            m = _CHART_MARKER_RE.match(str(cell or "").strip())
            if m and m.group(1) not in seen:
                seen.append(m.group(1))
    return seen


def _chart_detail_section(tag: str, chart_store_row, workfile_state, full_unit_set: dict) -> str:
    """
    One markdown section for a single referenced Chart Store entry: its
    own settings, its complete rendering source, and its live
    population_layers -- the same three things a stand-alone Custom
    Charts bundle would show for this exact chart.
    """
    if chart_store_row is None:
        return f"""

## Chart {tag}

No Chart Store entry with this id exists in the workfile any more --
this marker cell will render as an empty rectangle (the reserved space
is still drawn; nothing is composited into it).
"""

    base_chart_name = str(chart_store_row.get("base_chart_name", "") or "")
    try:
        source = _get_chart_source(base_chart_name, workfile_state.custom_chart_code)
    except ValueError as e:
        return f"\n## Chart {tag}\n\nCould not resolve base_chart_name: {e}\n"

    population_layers = resolve_chart_store_population_layers(chart_store_row, workfile_state, full_unit_set)
    layers_json = _layers_to_json(population_layers)

    settings_lines = "\n".join(
        f"- `{field}` = `{chart_store_row.get(field, '')}`"
        for field in (
            "base_chart_name", "cache_file", "populations",
            "start_period", "end_period", "metric_periods",
            "width_emu", "height_emu", "tweaks", "description",
        )
    )

    return f"""

## Chart {tag} -- Chart Store id `{chart_store_row.get('chart_store_id', '')}`, embedded in this table via the literal marker text "{{{tag}}}"

This chart is not rendered by the table's own code. The table function's
only job for this cell is recognising the marker string above and
reporting back the rectangle it reserved for it (the `chart_cells` return
value alongside `image_bytes`). The chart itself is
rendered completely separately, using `base_chart_name` below, at that
reserved rectangle's own width/height (never this row's own stored
width_emu/height_emu), then composited as a second, layered image on top
of the table's own -- a PowerPoint picture layered after the table's own
in the final report, or a nested SVG `<image>` spliced into the table's
own SVG in the Output Tables Preview. To fully rebuild what this table
looks like, this chart must be rendered independently using the code and
data below, then placed at that same reserved rectangle -- the table's
own code never does this itself, and does not need to.

### Settings

Same fields a Running Order `insert_chart` row or the Charts sheet's own
sandbox holds for this chart:

{settings_lines}

### Chart source ("{base_chart_name}")

```python
{source}
```

### Live population_layers for this chart, right now

```json
{layers_json}
```
"""


def build_bundle(table_type_ref: str, content: list, column_widths: list, row_heights: list,
                 width_emu: int, height_emu: int, tweaks: str, custom_table_code: dict = None,
                 include_charts: bool = False, workfile_state=None, full_unit_set: dict = None) -> str:
    """
    Build the complete Custom Tables download document for one table, as
    currently configured and rendering on screen.

    include_charts=True additionally resolves and includes full detail
    for every Chart Store entry referenced by a "{Cn}" marker anywhere in
    `content` -- requires workfile_state (for chart_store_rows/cache/
    custom_chart_code) and full_unit_set (for population resolution); the
    caller (output_tables_tab/preview.py) already computes both for its own
    Preview splice, so they're passed straight through, not recomputed
    here.
    """
    source = _get_table_source(table_type_ref, custom_table_code)
    live_data = _grid_to_json(content, column_widths, row_heights)

    chart_sections = ""
    if include_charts and workfile_state is not None:
        referenced_ids = _referenced_chart_store_ids(content)
        if referenced_ids:
            chart_store_by_id = {r.get("chart_store_id"): r for r in workfile_state.chart_store_rows}
            how_it_fits_together = """

## How the embedded chart(s) below fit together with this table

This table's `content` grid (in the live data section above) contains one
or more cells whose entire text is a literal marker like `{C3}` -- a
Chart Store id, wrapped in curly braces. Rendering this table correctly
means two separate steps, always in this order, never one merged step:

1. Run this table's own code (below) against `content`/`column_widths`/
   `row_heights`/`width_emu`/`height_emu`/`tweaks` exactly as documented
   in the table_inputs contract above. For each `{Cn}` cell, this table's
   own code does NOT draw any text for it -- it recognises the marker,
   reserves space for it, and returns that reservation as a rectangle
   (`{"x", "y", "width", "height"}`, all in EMU) inside the `chart_cells`
   dict this function returns alongside `image_bytes`.
2. For each `(tag, rectangle)` pair in `chart_cells`, render that chart's
   own code (in its own "Chart {tag}" section below) using that chart's
   own live `population_layers` (also below), called with
   `width_emu=rectangle["width"]` and `height_emu=rectangle["height"]`
   -- never this table's own `width_emu`/`height_emu`, and never the
   Chart Store entry's own stored `width_emu`/`height_emu` either. Layer
   the result on top of the table's own image at that rectangle's `x`/`y`
   position. This second image is never merged into or redrawn as part of
   the table's own picture -- it sits on top of it, as its own separate
   image.

Every chart referenced this way is fully detailed in its own section
below -- settings, complete source, and live data -- so it can be
rendered and composited without needing anything beyond this document.
"""
            sections = [how_it_fits_together]
            for tag in referenced_ids:
                sections.append(
                    _chart_detail_section(tag, chart_store_by_id.get(tag), workfile_state, full_unit_set)
                )
            chart_sections = "".join(sections)

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

width_emu = {width_emu}
height_emu = {height_emu}
tweaks = "{tweaks}"

```json
{live_data}
```
{chart_sections}"""
