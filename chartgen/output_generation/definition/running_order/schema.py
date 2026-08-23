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

# The Charts sheet sandbox's round-trip field list for one insert_chart row.
# A single list, so extending the round-trip later is a one-line change here
# rather than a rework of the sync logic.
#
# width_emu/height_emu are always edited through the sandbox's percent unit,
# never as raw EMU. start_period/end_period/metric_periods store the value
# exactly as picked or typed, and are never rewritten or reconstructed;
# extraction of the numeric id happens once, in cut_resolution. Schema in
# docs/DATA_FORMATS.md.
CHART_SANDBOX_FIELDS = ["base_chart_name", "cache_file", "populations",
                        "start_period", "end_period", "metric_periods",
                        "width_emu", "height_emu", "tweaks"]

# insert_table's own round-trip field list. No cache_file, populations or
# period fields: a table has no data-shape cut of its own, and the grid it
# references resolves independently at render time.
TABLE_SANDBOX_FIELDS = ["table_id", "table_type_ref", "width_emu", "height_emu", "tweaks"]

# hyperlink_left/hyperlink_top/hyperlink_size/hyperlink_colour: optional,
# insert_chart only. left/top are an EMU offset from the chart's own
# top-right corner, NOT absolute slide coordinates, so the icon travels with
# the chart. Blank in either means no icon at all; (0, 0) is a valid value
# and is not the same as blank. Defaults in docs/DATA_FORMATS.md.
