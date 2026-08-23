"""
charts_tab
The Charts sheet: a sandbox for previewing and tuning chart rendering,
wired as a two-way sync with the Running Order.

Full description of the flow, and the rule that the order of these
sections cannot change, in sheet.py.

| Module | Owns |
|---|---|
| `sheet.py` | The tab entry point and the order every section renders in |
| `selection.py` | The Select Chart box: both entry points and the Data shape picker |
| `periods.py` | Period Range and Convert to Metrics, TimeSeries only |
| `save_back.py` | Save to Running Order and Save to Chart Store |
| `authoring.py` | The Custom Charts round-trip, and Export Picture |
| `preview.py` | The rendered chart, summary stats and unit lists |
| `chart_store_area.py` | The Chart Store table shown in place of the preview |
| `state.py` | Restore, capture, and the three clears |
| `constants.py` | Zoom options, key prefix, placeholders, referencing-key lists |
| `helpers.py` | The one helper used by more than one of the above |

Only the two names below are used from outside this package.
"""

from chartgen.ui.tabs.charts_tab.sheet import render_charts_tab
from chartgen.ui.tabs.charts_tab.state import capture_charts_sheet_state

__all__ = ["render_charts_tab", "capture_charts_sheet_state"]
