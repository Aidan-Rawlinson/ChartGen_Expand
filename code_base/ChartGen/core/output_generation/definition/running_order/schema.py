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
