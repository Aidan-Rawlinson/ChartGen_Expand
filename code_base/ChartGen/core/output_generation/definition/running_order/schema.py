"""
schema.py
Running Order column schema, function names, scope values, and the
function-name groupings used to classify a row's behaviour.
"""

COLUMNS = [
    "row_id",
    "enabled",
    "scope",
    "function",
    "slide_index",
    "base_chart_name",
    "cache_file",
    "table_id",
    "table_type_ref",
    "populations",
    "start_period",
    "end_period",
    "metric_periods",
    "image_path",
    "excel_path",
    "export_range",
    "driver_range",
    "left_emu",
    "top_emu",
    "width_emu",
    "height_emu",
    "hyperlink_left",
    "hyperlink_top",
    "hyperlink_size",
    "hyperlink_colour",
    "tweaks",
    "tweaks",
    "notes",
]

ALL_FUNCTIONS = [
    "create_ppt",
    "set_default_populations",
    "update_text",
    "insert_chart",
    "insert_table",
    "insert_picture",
    "insert_from_excel",
    "open_excel",
    "close_excel",
    "empty_placeholder",
    "save_ppt",
    "save_pdf",
]

SCOPE_VALUES = ["normal", "batch_open", "batch_close"]

STRUCTURAL_FUNCTIONS = {"create_ppt", "set_default_populations", "update_text", "save_ppt", "save_pdf"}
CONTENT_FUNCTIONS    = {"insert_chart", "insert_table", "insert_picture", "insert_from_excel", "empty_placeholder"}
BATCH_FUNCTIONS      = {"open_excel", "close_excel"}

# Fields the Charts sheet sandbox reads from, and writes back to, a single
# insert_chart Running Order row. A single list so extending the round-trip
# later (e.g. a future shape-specific analytical field) is a one-line change
# here rather than a rework of the sync logic itself. width_emu/height_emu
# are always edited via the sandbox's percent-of-page-size unit
# (core.shared.infrastructure.page_sizing), never as raw EMU.
# start_period/end_period store period_id (stable identity), not the
# display label — only meaningful for a TimeSeries cache_file; blank means
# the full period range, the same "blank = inherit/default" convention as
# populations.
# metric_periods is a different concept — a '^'-delimited list of one or
# more individual period_ids (not a range) that converts a TimeSeries
# cache_file into a snapshot NumericSeries at insert_chart time (see
# core.shared.normalisation_containers.shape_transforms), one output metric
# per source Metric-Series x selected period. Blank means no conversion —
# the row renders as an ordinary TimeSeries chart, same as before this
# field existed.
# tweaks is a free-text string passed straight through to the Base Chart
# function's own `tweaks` parameter (Decisions.md), uninterpreted by
# anything in the Running Order/assembly layer. Blank means "no tweaks" —
# a nil-length string is what a Base Chart receives when the row's tweaks
# column is empty.
CHART_SANDBOX_FIELDS = ["base_chart_name", "cache_file", "populations",
                        "start_period", "end_period", "metric_periods",
                        "width_emu", "height_emu", "tweaks"]

# insert_table's own round-trip field list, mirroring CHART_SANDBOX_FIELDS
# for the Output Tables sandbox -- no cache_file/populations/period fields
# (a table has no data-shape cut of its own; the grid it references does
# its own resolution independently, per row, at render time), just table
# identity, table_type_ref, size, and tweaks.
TABLE_SANDBOX_FIELDS = ["table_id", "table_type_ref", "width_emu", "height_emu", "tweaks"]

# hyperlink_left/hyperlink_top/hyperlink_size/hyperlink_colour — optional,
# insert_chart only. An icon is drawn onto the slide after the chart image
# itself, marking that the chart links out to its own source data.
# hyperlink_left/hyperlink_top are NOT absolute slide coordinates: they are
# an EMU offset from the chart's own top-right corner (left_emu + width_emu,
# top_emu) — so the icon's position travels with the chart, not the slide.
# Blank in either one means no icon is drawn at all for this row; (0, 0) is
# a valid, meaningful value (icon's own top-left corner sits exactly at the
# chart's top-right corner), not the same thing as blank. hyperlink_size is
# the icon's own width/height in EMU (drawn square) — blank defaults to
# roughly 1cm (360000 EMU). hyperlink_colour is a hex string — blank
# defaults to the standard Office hyperlink blue (#0563C1).

