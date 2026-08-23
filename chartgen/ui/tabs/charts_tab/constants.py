"""
constants.py
Zoom options, the session-key prefix, the dropdown placeholder sentinels,
and the two lists of sandbox keys that reference a specific entity.

Split out so every module in this package reads the same values without
importing each other.
"""

ZOOM_OPTIONS = ["0.75x", "Actual size (approximately)", "1.25x", "1.5x", "2x", "Fit to screen"]
ZOOM_MULTIPLIERS = {"0.75x": 0.75, "Actual size (approximately)": 1.0, "1.25x": 1.25, "1.5x": 1.5, "2x": 2.0}
DEFAULT_ZOOM = "Actual size (approximately)"
CS_KEY_PREFIX = "cs_"

# Placeholder option values, used as literal entries in each dropdown's own
# options list rather than Python None — None triggers Streamlit's own
# built-in "Choose an option" placeholder once pre-set into session_state,
# which fights with a custom format_func. A plain string sentinel avoids
# that ambiguity entirely and doubles as the box's display text when
# nothing is selected.
RO_PLACEHOLDER = "- Running order line -"
SHAPE_PLACEHOLDER = "- Chart list -"
TARGET_PLACEHOLDER = "- Select target row -"
CHART_STORE_PLACEHOLDER = "- Chart Store line -"
CHART_STORE_TARGET_PLACEHOLDER = "- Select Chart Store entry -"

# Sandbox state referencing a specific Running Order row by row_id — cleared
# after every save, since an Insert renumbers row_ids after the insertion
# point and an Overwrite changes the very fields a stale label would show.
ROW_REFERENCING_KEYS = [
    "cs_ro_choice", "cs_last_loaded_ro", "cs_bound_row_idx",
    "cs_bound_shape_type", "cs_target_row_choice",
]

# Chart Store's own equivalent of ROW_REFERENCING_KEYS — cleared whenever a
# Running Order row load takes over the sandbox, so the two entry points
# stay mutually exclusive (selecting one always clears the other's own
# selectbox back to its placeholder, rather than leaving a stale selection
# on screen that no longer matches what's actually bound).
CHART_STORE_REFERENCING_KEYS = [
    "cs_chart_store_choice", "cs_last_loaded_chart_store", "cs_bound_chart_store_id",
    "cs_chart_store_target_choice",
]
