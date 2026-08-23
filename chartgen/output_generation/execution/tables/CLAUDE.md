# tables

## The grid

An Output Table is a grid of constant text and Stat Tag values, composited into one image by a Base Table function.

Stored in the shape it is authored in: an (N+1) by (M+1) spreadsheet-shaped CSV. Row 0 and column 0 hold column widths, row heights, and the table's own id in the corner cell. The rest is content.

Widths and heights are percentages of the table's own total, each expected to sum to about 100%. Validated on an explicit Update, tolerance plus or minus 0.5%, and never auto-corrected.

Every table starts at `DEFAULT_TABLE_ROWS` by `DEFAULT_TABLE_COLUMNS`, whatever created it. There is no size choice at creation.

There is no fixed grid column schema. Each grid is written from its own rows' keys.

## Resolution

`resolve.py` is the single point where a grid becomes plain values for a renderer. It substitutes Stat Tags through `text_engine.build_stat_tag_tokens`, the same token map `update_text` builds, and converts `<br>`, `<br/>` and `<br />`, case-insensitive, into a real newline. Both the final report and the tab preview go through it.

## Chart cells

A `{Cn}` cell names a Chart Store entry. `insert_table` renders it sized to the cell's own reported rectangle, never the entry's stored size, and layers it as a second picture after the table's own.

The reported rectangle arrives in inflated render space. Divide by the render scale when placing the picture, never when calling the renderer.

A Chart Store entry with a blank `populations` inherits the Running Order default. `insert_table` reads it from `AssemblyContext`. The tab preview, having no context, reads the `set_default_populations` row off `running_order_rows` instead.

## Excel

`grid_xlsx.py` reads a cell through `cell.number_format` as well as `cell.value`. Excel stores a typed `5%` as the float `0.05` with a percentage format, so reading the value alone loses the percentage entirely. A format containing `%` means multiply back up by 100, round, and append `%`.
