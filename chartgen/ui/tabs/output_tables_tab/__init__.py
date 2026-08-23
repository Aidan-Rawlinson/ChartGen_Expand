"""
output_tables_tab
Output Tables: grid-based tables rendered as a single image, the table
equivalent of a Base Chart. Authored here rather than on the Charts
sheet, since an Output Table's content model does not fit
CHART_SANDBOX_FIELDS.

One selection, at the top: a "Select Table" box holding both entry
points, a Running Order row (bound mode) and an Output Table by name
(free-play). "+ New Output Table" sits last in that list and reveals an
inline Name/Create control. Everything below acts on that one selection.
There is no second selector anywhere on the tab.

Edit Grid is content authoring: the raw c0..cN grid, resize, Update, and
the Excel round-trip. Preview mirrors the Charts sheet's mechanics
wherever the concepts match: table type, tweaks, sizing in percent,
save-back via row_ops.py, Custom Tables, and Reset. Reset clears
Preview's own configuration only, never the table selection, which lives
in the shared box above.

A "{Cn}" chart-component cell references a Chart Store entry, rendered
live in Preview as a nested <image> spliced into the table's own SVG, and
in the final report as a layered PowerPoint picture. Neither path
composites the two SVG documents into one.

Creating a table here also appends an insert_table row immediately above
save_ppt, with no slide or position yet.

| Module | Owns |
|---|---|
| `sheet.py` | The tab entry point: the shared Select Table box and the mode switch |
| `grid_editor.py` | Edit Grid mode |
| `preview.py` | Preview mode |
| `new_table.py` | The inline "+ New Output Table" form |
| `chart_cells.py` | "{Cn}" chart cells, and this package's _svg_preview_html |
| `state.py` | Restore, capture and Reset of sandbox state |
| `constants.py` | Placeholders, zoom options, the session-key prefix |

Only the two names below are used from outside this package.
"""

from chartgen.ui.tabs.output_tables_tab.sheet import render_output_tables_tab
from chartgen.ui.tabs.output_tables_tab.state import capture_output_tables_sheet_state

__all__ = ["render_output_tables_tab", "capture_output_tables_sheet_state"]
