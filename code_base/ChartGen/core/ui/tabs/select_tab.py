"""
select_tab.py
Select tab — reporting unit selection and the Populations table.

_units_to_display_rows is a units-table reshape (service-expansion into one
row per service) used only by this tab's Populations table, so it stays here
rather than moving to workfile.state — nothing else needs it, and workfile.state
is a data store, not a place for display-shaping logic.
"""

import streamlit as st

from core.workfile.state.session_state import ws, settings, save_settings, units


def _units_to_display_rows(rows: list, expand_services: bool = False) -> list:
    """Prepare unit rows for display in the Populations table, optionally expanding services into one row each."""
    if not expand_services:
        return rows

    expanded = []
    for row in rows:
        ids   = [v for v in row["service_item_ids"].split("|")          if v] if row["service_item_ids"] else []
        names = [v for v in row["service_item_names"].split("|")        if v] if row["service_item_names"] else []
        counts= [v for v in row["service_response_counts"].split("|")   if v] if row["service_response_counts"] else []

        if not ids:
            expanded.append(row)
        else:
            for i, sid in enumerate(ids):
                expanded.append({
                    **row,
                    "service_item_ids":          sid,
                    "service_item_names":         names[i] if i < len(names) else "",
                    "service_response_counts":    counts[i] if i < len(counts) else "",
                })
    return expanded


def render_select_tab():
    import pandas as pd

    st.header("Selection & Populations")
    the_units = units()

    st.subheader("Select reporting unit")

    if not the_units:
        st.warning("No units loaded.")
    else:
        display_mode = st.radio(
            "Identify by",
            options=["Unit name", "Unit code", "Unit ID"],
            horizontal=True, key="select_display_mode",
        )

        def _unit_label(row):
            if display_mode == "Unit code":
                return f"{row['unit_code']}  —  {row['unit_name']}"
            elif display_mode == "Unit ID":
                return f"{row['unit_id']}  —  {row['unit_name']}"
            else:
                return row["unit_name"]

        label_to_id = {_unit_label(r): r["unit_id"] for r in the_units}
        saved_unit = settings().get("selected_unit_id", "")
        saved_label = next((lbl for lbl, sid in label_to_id.items() if sid == saved_unit), None)
        unit_index = list(label_to_id.keys()).index(saved_label) if saved_label in label_to_id else None

        selected_label = st.selectbox(
            "Reporting unit", options=list(label_to_id.keys()), index=unit_index,
            placeholder="Select a reporting unit…", key="select_unit",
        )
        selected_id = label_to_id.get(selected_label, "")

        if selected_id:
            if selected_id != saved_unit:
                s = settings()
                s["selected_unit_id"] = str(selected_id)
                save_settings(s)

            selected_row = next((r for r in the_units if r["unit_id"] == selected_id), None)
            if selected_row:
                c1, c2, c3 = st.columns(3)
                c1.metric("Unit ID",      selected_row["unit_id"])
                c2.metric("Code",         selected_row["unit_code"])
                c3.metric("Organisation", selected_row["organisation_name"])

    st.divider()
    st.subheader("Populations")
    st.caption("Population tables define the population.")

    with st.expander("Units — population table", expanded=st.session_state.get("pop_expander_open", True)):
        if not the_units:
            st.info("No unit data.")
        else:
            col_toggle1, col_toggle2 = st.columns([2, 2])
            expand_services = col_toggle1.toggle(
                "Show services as separate rows",
                value=st.session_state.get("pop_expand_services_val", False), key="pop_expand_services",
            )
            include_org = col_toggle2.toggle(
                "Include organisational-level submissions",
                value=st.session_state.get("pop_include_org_val", False), key="pop_include_org",
            )
            st.session_state["pop_expand_services_val"] = expand_services
            st.session_state["pop_include_org_val"] = include_org
            st.session_state["pop_expander_open"] = True

            display_rows = the_units if include_org else [
                r for r in the_units if r.get("submission_level", "") != "O"
            ]
            display_rows = _units_to_display_rows(display_rows, expand_services)

            display_cols = [
                "unit_id", "unit_code", "unit_name",
                "organisation_name", "response_count", "submission_service_count",
                "service_item_ids", "service_item_names", "service_response_counts", "Region()",
            ]
            df = pd.DataFrame(display_rows)[display_cols] if display_rows else pd.DataFrame(columns=display_cols)
            df.columns = [
                "ID", "Code", "Name", "Organisation", "Responses", "Service count",
                "Service IDs", "Service names", "Service responses", "Region()",
            ]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(display_rows)} row(s)")
