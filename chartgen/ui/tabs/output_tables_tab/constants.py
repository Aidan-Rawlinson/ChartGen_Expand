"""
constants.py
Placeholders, zoom options and the session-key prefix for the Output
Tables tab. Split out so every module in this package reads the same
values without importing each other.
"""

NEW_TABLE_OPTION = "+ New Output Table"
RO_PLACEHOLDER = "- Running order line -"
TABLE_PLACEHOLDER = "- Saved Table -"
TARGET_PLACEHOLDER = "- Select target row -"

# Screen zoom for the Preview image. Display only, never saved.
#
# An explicit pixel width is required: st.image() otherwise shows the render
# at its full native resolution rather than a size reflecting the configured
# width and height percentage.
ZOOM_OPTIONS = ["0.75x", "Actual size (approximately)", "1.25x", "1.5x", "2x", "Fit to screen"]
ZOOM_MULTIPLIERS = {"0.75x": 0.75, "Actual size (approximately)": 1.0, "1.25x": 1.25, "1.5x": 1.5, "2x": 2.0}
DEFAULT_ZOOM = "Actual size (approximately)"

# "ots_" is Preview's own configuration state (table type, tweaks, sizing,
# save-back target, paste-back) -- what Reset clears. Table *selection*
# ("ot_ro_choice", "ot_table_choice", "ot_bound_row_idx", ...) lives outside
# that prefix on purpose, so Reset never disturbs which table is selected.
OTS_KEY_PREFIX = "ots_"
