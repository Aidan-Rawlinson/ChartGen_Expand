"""
save_back.py
The two save-back surfaces: Save to Running Order (Overwrite, Insert
above, Insert below) and Save to Chart Store (Add, Overwrite).

A Chart Store entry has no position, so its save offers Add and Overwrite
only, never Insert -- the store is flat and unordered.

Both write only on an explicit button press, and both recompute their own
values rather than reaching across to the preview column.
"""

import streamlit as st

from chartgen.output_generation.definition.running_order import (
    CHART_SANDBOX_FIELDS, overwrite_row_fields, insert_new_row,
)
from chartgen.output_generation.execution.charts.chart_store import next_chart_store_id
from chartgen.ui.tabs.charts_tab.constants import (
    CHART_STORE_TARGET_PLACEHOLDER, TARGET_PLACEHOLDER,
)
from chartgen.ui.tabs.charts_tab.state import _clear_row_referencing_state


def _render_save_back(workfile_state, ro_choice, chart_row_ids, chart_store_ids, row_id_to_idx,
                      format_target_choice, format_chart_store_choice,
                      base_chart_name, selected_file, populations_str,
                      start_period_to_save, end_period_to_save, metric_periods_to_save,
                      width_emu, height_emu, tweaks_str):
    """
    Render both save-back expanders. The long argument list is the
    sandbox's current configuration, passed explicitly rather than
    re-derived here -- what gets saved must be exactly what is on screen.
    """
    # --- Save to Running Order ---
    target_default = ro_choice if ro_choice in chart_row_ids else TARGET_PLACEHOLDER
    current_target = st.session_state.get("cs_target_row_choice", target_default)
    if current_target not in chart_row_ids:
        current_target = TARGET_PLACEHOLDER
    st.session_state.setdefault("cs_target_row_choice", current_target)
    if st.session_state.get("cs_target_row_choice") not in ([TARGET_PLACEHOLDER] + chart_row_ids):
        st.session_state["cs_target_row_choice"] = TARGET_PLACEHOLDER

    with st.expander("Save to Running Order", expanded=False):
        st.session_state.setdefault("cs_action", "Overwrite selected row")
        st.caption("Action")
        action = st.selectbox(
            "Action",
            options=["Overwrite selected row", "Insert above selected row", "Insert below selected row"],
            key="cs_action", label_visibility="collapsed",
        )
        st.caption("Target Running Order row")
        target_choice = st.selectbox(
            "Target Running Order row", options=[TARGET_PLACEHOLDER] + chart_row_ids,
            format_func=format_target_choice, key="cs_target_row_choice",
            label_visibility="collapsed",
        )
        save_clicked = st.button("💾  Save to Running Order", type="primary", use_container_width=True)

    if save_clicked:
        if target_choice == TARGET_PLACEHOLDER:
            st.error("Select a target Running Order row first.")
        elif not base_chart_name:
            st.error("Select a chart type before saving.")
        else:
            target_idx = row_id_to_idx[target_choice]
            field_value_builders = {
                "base_chart_name": lambda: base_chart_name,
                "cache_file":     lambda: selected_file,
                "populations":    lambda: populations_str,
                "start_period":   lambda: start_period_to_save,
                "end_period":     lambda: end_period_to_save,
                "metric_periods": lambda: metric_periods_to_save,
                "width_emu":      lambda: width_emu,
                "height_emu":     lambda: height_emu,
                "tweaks":         lambda: tweaks_str,
            }
            field_values = {f: field_value_builders[f]() for f in CHART_SANDBOX_FIELDS}

            if action == "Overwrite selected row":
                overwrite_row_fields(workfile_state.running_order_rows, target_idx, field_values)
            elif action == "Insert above selected row":
                insert_new_row(workfile_state.running_order_rows, target_idx, field_values, "above")
            else:
                insert_new_row(workfile_state.running_order_rows, target_idx, field_values, "below")
            workfile_state.dirty = True
            # row_id references shift on Insert, and this row's own displayed
            # content just changed on Overwrite — clear rather than risk a
            # stale reference on the next rerun.
            _clear_row_referencing_state()
            st.success("Saved to Running Order.")
            st.rerun()

    # --- Save to Chart Store — a flat, unordered store, so unlike
    # Save to Running Order there is no position/sequence to give:
    # just Add (always a new entry) or Overwrite (an existing one,
    # picked below). A Chart Store Line loaded above defaults this to
    # Overwrite that same entry, mirroring how a bound Running Order
    # row defaults its own save to Overwrite. ---
    with st.expander("Save to Chart Store", expanded=False):
        st.session_state.setdefault("cs_chart_store_action", "Add new entry")
        st.caption("Action")
        chart_store_action = st.selectbox(
            "Action", options=["Add new entry", "Overwrite selected entry"],
            key="cs_chart_store_action", label_visibility="collapsed",
        )
        st.caption("Target Chart Store entry")
        chart_store_target_choice = st.selectbox(
            "Target Chart Store entry", options=[CHART_STORE_TARGET_PLACEHOLDER] + chart_store_ids,
            format_func=format_chart_store_choice, key="cs_chart_store_target_choice",
            label_visibility="collapsed",
        )
        st.caption("Description (optional)")
        chart_store_description = st.text_input(
            "Description", key="cs_chart_store_description", label_visibility="collapsed",
        )
        save_to_chart_store_clicked = st.button(
            "🗂  Save to Chart Store", type="primary", use_container_width=True,
        )

    if save_to_chart_store_clicked:
        if not base_chart_name:
            st.error("Select a chart type before saving.")
        elif chart_store_action == "Overwrite selected entry" and chart_store_target_choice == CHART_STORE_TARGET_PLACEHOLDER:
            st.error("Select a Chart Store entry to overwrite first.")
        else:
            field_values = {
                "base_chart_name": base_chart_name,
                "cache_file":      selected_file,
                "populations":     populations_str,
                "start_period":    start_period_to_save,
                "end_period":      end_period_to_save,
                "metric_periods":  metric_periods_to_save,
                "width_emu":       width_emu,
                "height_emu":      height_emu,
                "tweaks":          tweaks_str,
                "description":     chart_store_description,
            }
            if chart_store_action == "Add new entry":
                saved_id = next_chart_store_id(
                    workfile_state.settings,
                    {r.get("chart_store_id") for r in workfile_state.chart_store_rows},
                )
                workfile_state.chart_store_rows.append({"chart_store_id": saved_id, **field_values})
            else:
                saved_id = chart_store_target_choice
                for row in workfile_state.chart_store_rows:
                    if row.get("chart_store_id") == saved_id:
                        row.update(field_values)
                        break
            workfile_state.dirty = True
            # "cs_chart_store_choice"/"cs_chart_store_target_choice" are
            # widget-bound keys already instantiated earlier this run —
            # staged the same way "ot_pending_ro_choice_after_save" is,
            # applied at the top of render_charts_tab before those
            # selectboxes are created on the next run.
            st.session_state["cs_pending_chart_store_choice_after_save"] = saved_id
            st.session_state["cs_pending_chart_store_target_after_save"] = saved_id
            st.session_state.pop("cs_last_loaded_chart_store", None)
            st.success("Saved to Chart Store.")
            st.rerun()
