"""
select_tab.py
Reporting unit selection — picks the reporting unit from the master table,
then shows units in other tables related to it (one hop only, via
soft_parents). Population table display and reordering live on the
Populations tab.
"""

import streamlit as st

from core.shared.infrastructure.soft_parents import resolve_full_unit_set
from core.ui.common.formatting import population_table_columns, display_column_labels
from core.ui.common.guidance import render_tab_header
from core.workfile.state.session_state import settings, save_settings, master_table, ws


def render_select_tab():
    render_tab_header("Reporting unit selection", "select")
    the_units = master_table()

    if not the_units:
        st.warning("No units loaded.")
        return

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

    if not selected_id:
        return

    if selected_id != saved_unit:
        s = settings()
        s["selected_unit_id"] = str(selected_id)
        save_settings(s)

    selected_row = next((r for r in the_units if r["unit_id"] == selected_id), None)
    if not selected_row:
        return

    c1, c2 = st.columns(2)
    c1.metric("Unit ID", selected_row["unit_id"])
    c2.metric("Code",    selected_row["unit_code"])

    workfile_state = ws()
    master_table_name = workfile_state.table_order[0] if workfile_state.table_order else ""
    full_unit_set = resolve_full_unit_set(selected_row, master_table_name, workfile_state.tables)

    st.divider()
    st.subheader("Full Unit(s)")

    # The reporting unit's own row (master table) always leads, bolded, so
    # this becomes one lookup table: for this reporting unit, its matching
    # row(s) in every table it appears in (itself, then everything one hop
    # out). A table can hold more than one row here — e.g. an organisation
    # supporting two ICBs — that's expected, not a display bug.
    combined_rows = [(master_table_name, r) for r in full_unit_set.get(master_table_name, [])]
    cols = list(population_table_columns([selected_row]))
    for table_name, rows in full_unit_set.items():
        if table_name == master_table_name:
            continue
        for r in rows:
            combined_rows.append((table_name, r))
            for c in population_table_columns([r]):
                if c not in cols:
                    cols.append(c)

    import pandas as pd

    data = []
    for table_name, r in combined_rows:
        entry = {"Source table": table_name}
        for c in cols:
            entry[c] = r.get(c, "")
        data.append(entry)

    df = pd.DataFrame(data)[["Source table"] + cols]
    df.columns = ["Source table"] + display_column_labels(cols)

    def _bold_reporting_unit_row(row):
        return ["font-weight: bold" if row.name == 0 else "" for _ in row]

    styled = df.style.apply(_bold_reporting_unit_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
