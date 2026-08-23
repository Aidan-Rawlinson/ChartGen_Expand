"""
state.py
Sandbox state persistence for the Output Tables tab: the once-per-Open
restore, the pre-Save capture into settings["output_tables_sheet_state"],
and the Reset that clears it all back out.

Mirrors the Charts sheet's own equivalents field-for-field for the table
domain.
"""

import json

import streamlit as st

from chartgen.shared.infrastructure.page_sizing import STANDARD_PAGE_SIZES_EMU
from chartgen.ui.tabs.output_tables_tab.constants import (
    OTS_KEY_PREFIX, RO_PLACEHOLDER, TARGET_PLACEHOLDER,
)


def _clear_sandbox_state():
    """
    Full reset -- clears both the shared table selection ("ot_" prefix)
    and Preview's own configuration ("ots_" prefix), mirroring the Charts
    sheet's Reset exactly (a single prefix there; two here, both wiped
    together) so a person can move on to a different table in one click.
    "ot_tab_rendered" is preserved so this doesn't re-trigger the once-per-
    Open restore from settings["output_tables_sheet_state"], which would
    otherwise silently undo the reset.
    """
    keep = {"ot_tab_rendered"}
    for k in list(st.session_state.keys()):
        if (k.startswith("ot_") or k.startswith(OTS_KEY_PREFIX)) and k not in keep:
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Sandbox state persistence (settings["output_tables_sheet_state"]),
# mirroring charts_tab/state.py's capture_charts_sheet_state / _restore_charts_sheet_state
# field-for-field for the table domain.
# ---------------------------------------------------------------------------

def _restore_output_tables_sheet_state(workfile_state, the_settings, row_id_to_idx):
    raw = (the_settings or {}).get("output_tables_sheet_state", "")
    if not raw:
        return
    try:
        state = json.loads(raw)
    except (TypeError, ValueError):
        return

    table_id = state.get("table_id", "")
    if table_id in workfile_state.output_tables:
        name = next(
            (r["table_name"] for r in workfile_state.output_table_rows if r["table_id"] == table_id), ""
        )
        if name:
            st.session_state["ot_table_choice"] = name
            st.session_state["ot_last_table_choice"] = name
            st.session_state["ot_selected_table_id"] = table_id

    ro_row_id = state.get("ro_row_id")
    if ro_row_id in row_id_to_idx:
        st.session_state["ot_ro_choice"] = ro_row_id
        st.session_state["ot_last_loaded_ro"] = ro_row_id
        st.session_state["ot_bound_row_idx"] = row_id_to_idx[ro_row_id]
    else:
        st.session_state["ot_ro_choice"] = RO_PLACEHOLDER
        st.session_state["ot_last_loaded_ro"] = RO_PLACEHOLDER

    st.session_state["ots_table_type_ref"] = state.get("table_type_ref", "plain_grid")
    st.session_state["ots_tweaks_str"] = state.get("tweaks", "")

    # A persisted value is shown exactly as stored, however small or large.
    # The Sizing box is a save-back surface, so any number substituted here
    # gets committed to the row on the next save. A value that will not
    # parse at all is reported rather than replaced silently; the key is
    # left unset and the setdefault further down supplies the starting
    # value, with the user told why.
    for key, label in (("width_pct", "Width"), ("height_pct", "Height")):
        raw = state.get(key, 50.0)
        try:
            st.session_state["ots_" + key] = float(raw)
        except (TypeError, ValueError):
            st.error(
                f"Stored Preview {label.lower()} ({raw!r}) is not a number, so it could not be "
                f"restored. The box below shows a starting value, not your stored one. Use Reset "
                f"to clear the saved Preview configuration."
            )

    manual_page_size = state.get("manual_page_size")
    if manual_page_size in STANDARD_PAGE_SIZES_EMU:
        st.session_state["ots_manual_page_size"] = manual_page_size

    action = state.get("action", "Overwrite selected row")
    if action in ("Overwrite selected row", "Insert above selected row", "Insert below selected row"):
        st.session_state["ots_action"] = action

    target_row_id = state.get("target_row_id")
    if target_row_id in row_id_to_idx:
        st.session_state["ots_target_row_choice"] = target_row_id


def capture_output_tables_sheet_state(workfile_state):
    """
    Snapshot the tab's current table selection and Preview configuration
    into settings["output_tables_sheet_state"] (JSON), called just before
    Save/Save As/Save and Close (sidebar.py, save_as_form.py), mirroring
    capture_charts_sheet_state.
    """
    if "ot_tab_rendered" not in st.session_state:
        return

    ro_choice = st.session_state.get("ot_ro_choice", RO_PLACEHOLDER)
    target_choice = st.session_state.get("ots_target_row_choice", TARGET_PLACEHOLDER)

    state = {
        "table_id": st.session_state.get("ot_selected_table_id", ""),
        "ro_row_id": ro_choice if ro_choice != RO_PLACEHOLDER else None,
        "table_type_ref": st.session_state.get("ots_table_type_ref", "plain_grid"),
        "tweaks": st.session_state.get("ots_tweaks_str", ""),
        "width_pct": st.session_state.get("ots_width_pct", 50.0),
        "height_pct": st.session_state.get("ots_height_pct", 50.0),
        "manual_page_size": st.session_state.get("ots_manual_page_size"),
        "action": st.session_state.get("ots_action", "Overwrite selected row"),
        "target_row_id": target_choice if target_choice != TARGET_PLACEHOLDER else None,
    }
    workfile_state.settings["output_tables_sheet_state"] = json.dumps(state)
