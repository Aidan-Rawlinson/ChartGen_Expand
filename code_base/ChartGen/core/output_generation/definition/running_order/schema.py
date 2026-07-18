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
    "placeholder",
    "chart_type_ref",
    "cache_file",
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
    "notes",
]

ALL_FUNCTIONS = [
    "create_ppt",
    "set_default_populations",
    "update_text",
    "insert_chart",
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
CONTENT_FUNCTIONS    = {"insert_chart", "insert_picture", "insert_from_excel", "empty_placeholder"}
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
CHART_SANDBOX_FIELDS = ["chart_type_ref", "cache_file", "populations",
                        "start_period", "end_period", "metric_periods",
                        "width_emu", "height_emu"]
