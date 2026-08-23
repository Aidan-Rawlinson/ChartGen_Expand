"""
sheet.py
Output Tables tab entry point: the one shared "Select Table" box holding
both entry points -- a Running Order row (bound mode) and an Output Table
by name (free-play) -- then the Edit Grid / Preview mode switch.

Everything below the box acts on that one selection. There is no second
selector anywhere on the tab.
"""

import streamlit as st

from chartgen.shared.infrastructure.page_sizing import emu_to_percent, get_page_size_emu
from chartgen.ui.common.guidance import render_tab_header
from chartgen.ui.tabs.output_tables_tab.constants import (
    NEW_TABLE_OPTION, RO_PLACEHOLDER, TABLE_PLACEHOLDER,
)
from chartgen.ui.tabs.output_tables_tab.grid_editor import _render_grid_editor
from chartgen.ui.tabs.output_tables_tab.new_table import _render_new_table_form
from chartgen.ui.tabs.output_tables_tab.preview import _render_preview_sandbox
from chartgen.ui.tabs.output_tables_tab.state import _restore_output_tables_sheet_state
from chartgen.workfile.state.session_state import ws, settings


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tab entry point -- the one shared "Select Table" box, then mode + content
# ---------------------------------------------------------------------------

def render_output_tables_tab():
    render_tab_header("Output Tables and Grids", "output_tables")

    workfile_state = ws()
    the_settings = settings()

    table_rows = workfile_state.output_table_rows
    name_to_id = {r["table_name"]: r["table_id"] for r in table_rows}
    id_to_name = {v: k for k, v in name_to_id.items()}
    table_names = list(name_to_id.keys())

    ro_rows = workfile_state.running_order_rows
    row_id_to_idx = {
        r["row_id"]: i for i, r in enumerate(ro_rows) if str(r.get("function", "")) == "insert_table"
    }
    table_row_ids = list(row_id_to_idx.keys())

    def ro_row_label(row_id):
        r = ro_rows[row_id_to_idx[row_id]]
        tid = str(r.get("table_id", "") or "")
        tname = id_to_name.get(tid, tid or "— no table —")
        ttype = str(r.get("table_type_ref", "") or "— no type —")
        return f"Row {row_id}: {ttype} · {tname}"

    def format_row_choice(v):
        return v if v == RO_PLACEHOLDER else ro_row_label(v)

    if "ot_tab_rendered" not in st.session_state:
        st.session_state["ot_tab_rendered"] = True
        _restore_output_tables_sheet_state(workfile_state, the_settings, row_id_to_idx)

    # Applied here, before the "Running Order row" selectbox below is
    # created, per the widget-bound-key restriction explained where this is
    # staged (Save to Running Order's success branch).
    if "ot_pending_ro_choice_after_save" in st.session_state:
        pending_ro = st.session_state.pop("ot_pending_ro_choice_after_save")
        if pending_ro in table_row_ids:
            st.session_state["ot_ro_choice"] = pending_ro
            # Also sync "last loaded" and the bound row index so the RO-row
            # detection block below sees this as unchanged, not a fresh
            # selection, and doesn't recompute Sizing from EMU a second
            # time — that redundant reload-after-save was the source of
            # the Sizing box occasionally going stale right after a save,
            # not a genuine new load.
            st.session_state["ot_last_loaded_ro"] = pending_ro
            st.session_state["ot_bound_row_idx"] = row_id_to_idx[pending_ro]

    if st.session_state.get("ot_ro_choice") not in ([RO_PLACEHOLDER] + table_row_ids):
        st.session_state["ot_ro_choice"] = RO_PLACEHOLDER

    with st.expander("Select Table", expanded=True):
        ro_choice = st.selectbox(
            "Running Order row", options=[RO_PLACEHOLDER] + table_row_ids,
            format_func=format_row_choice, key="ot_ro_choice",
        )

        last_loaded_ro = st.session_state.get("ot_last_loaded_ro", "__unset__")
        if ro_choice != last_loaded_ro:
            st.session_state["ot_last_loaded_ro"] = ro_choice
            if ro_choice == RO_PLACEHOLDER:
                st.session_state.pop("ot_bound_row_idx", None)
            else:
                row_idx = row_id_to_idx[ro_choice]
                row = ro_rows[row_idx]
                row_table_id = str(row.get("table_id", "") or "")
                page_w, page_h = get_page_size_emu(the_settings, st.session_state.get("ots_manual_page_size"))
                w_emu = _int_or_none(row.get("width_emu"))
                h_emu = _int_or_none(row.get("height_emu"))

                st.session_state["ot_bound_row_idx"] = row_idx
                st.session_state["ot_pending_table_choice"] = id_to_name.get(row_table_id)
                st.session_state["ots_pending_table_type_ref"] = str(row.get("table_type_ref", "") or "")
                st.session_state["ots_pending_tweaks_str"] = str(row.get("tweaks", "") or "")
                # The computed percentage is shown as it is, however small.
                # A tiny value means the row's stored EMU really is tiny
                # relative to the page, and that is what the widget should
                # say.
                width_pct_computed = round(emu_to_percent(w_emu, page_w, page_h), 2) if w_emu else 0.0
                height_pct_computed = round(emu_to_percent(h_emu, page_w, page_h), 2) if h_emu else 0.0
                st.session_state["ots_width_pct"] = width_pct_computed
                st.session_state["ots_height_pct"] = height_pct_computed
                st.session_state["ots_target_row_choice"] = ro_choice

        if "ot_pending_table_choice" in st.session_state:
            pending_label = st.session_state.pop("ot_pending_table_choice")
            if pending_label is not None:
                st.session_state["ot_table_choice"] = pending_label
        st.session_state.setdefault("ot_table_choice", TABLE_PLACEHOLDER)
        if st.session_state["ot_table_choice"] not in ([TABLE_PLACEHOLDER] + table_names + [NEW_TABLE_OPTION]):
            st.session_state["ot_table_choice"] = TABLE_PLACEHOLDER

        table_choice = st.selectbox(
            "Output Table", options=[TABLE_PLACEHOLDER] + table_names + [NEW_TABLE_OPTION], key="ot_table_choice",
        )

        if table_choice == NEW_TABLE_OPTION:
            _render_new_table_form(workfile_state, name_to_id, the_settings)

    if table_choice in (TABLE_PLACEHOLDER, NEW_TABLE_OPTION):
        return

    table_id = name_to_id[table_choice]
    st.session_state["ot_selected_table_id"] = table_id
    grid_rows = workfile_state.output_tables.get(table_id)
    if grid_rows is None:
        st.error("This Output Table's grid could not be found -- it may have been removed from the workfile.")
        return

    bound_row_idx = st.session_state.get("ot_bound_row_idx")
    if bound_row_idx is not None:
        bound_table_id = str(ro_rows[bound_row_idx].get("table_id", "") or "")
        if bound_table_id and bound_table_id != table_id:
            st.warning(
                "The bound Running Order row references a different Output "
                f"Table ('{id_to_name.get(bound_table_id, bound_table_id)}')."
            )

    st.session_state.setdefault("ot_mode", "Edit Grid")
    mode = st.radio(
        "Mode", options=["Edit Grid", "Preview"], key="ot_mode",
        horizontal=True, label_visibility="collapsed",
    )

    # Re-assert width_pct/height_pct from the bound row's stored EMU at the
    # moment Preview is entered, not only when the row was selected.
    #
    # Edit Grid is the default mode, so the original assignment happens while
    # the Sizing widget does not yet exist. Without this re-assertion
    # immediately before that widget's first mount, the box displays its own
    # min_value rather than the correct value, even though session_state
    # holds the right number throughout. Verified by testing.
    previous_mode = st.session_state.get("ot_previous_mode")
    entering_preview = (mode == "Preview" and previous_mode != "Preview")
    st.session_state["ot_previous_mode"] = mode

    if mode == "Preview" and entering_preview and bound_row_idx is not None:
        bound_row = ro_rows[bound_row_idx]
        page_w_r, page_h_r = get_page_size_emu(the_settings, st.session_state.get("ots_manual_page_size"))
        w_emu_r = _int_or_none(bound_row.get("width_emu"))
        h_emu_r = _int_or_none(bound_row.get("height_emu"))
        if w_emu_r:
            st.session_state["ots_width_pct"] = round(emu_to_percent(w_emu_r, page_w_r, page_h_r), 2)
        if h_emu_r:
            st.session_state["ots_height_pct"] = round(emu_to_percent(h_emu_r, page_w_r, page_h_r), 2)

    if mode == "Edit Grid":
        _render_grid_editor(workfile_state, table_id, grid_rows)
    else:
        _render_preview_sandbox(
            workfile_state, the_settings, table_id, grid_rows,
            table_row_ids, row_id_to_idx, id_to_name, ro_rows, ro_choice, format_row_choice,
        )
