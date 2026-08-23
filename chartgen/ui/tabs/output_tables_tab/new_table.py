"""
new_table.py
The inline "+ New Output Table" form, revealed inside the shared Select
Table box. Creating a table here also appends its insert_table Running
Order row immediately, with no slide or position yet.
"""

import streamlit as st

from chartgen.output_generation.definition.running_order import append_content_row_above_footer
from chartgen.output_generation.execution.tables.grid_store import (
    next_table_id, new_grid, DEFAULT_TABLE_ROWS, DEFAULT_TABLE_COLUMNS,
)
from chartgen.shared.infrastructure.page_sizing import percent_to_emu, get_page_size_emu


def _render_new_table_form(workfile_state, name_to_id, the_settings):
    st.caption("Create a new Output Table")
    new_name = st.text_input("Name", key="ot_new_name")

    if st.button("Create Output Table", type="primary", key="ot_create_table_btn"):
        name = new_name.strip()
        if not name:
            st.error("Enter a name.")
        elif name in name_to_id:
            st.error(f"'{name}' already exists. Choose a different name.")
        else:
            # Both the index rows and the grid store, since either can hold
            # an id the settings counter never saw.
            ids_in_use = {r.get("table_id") for r in workfile_state.output_table_rows}
            ids_in_use |= set(workfile_state.output_tables)
            table_id = next_table_id(workfile_state.settings, ids_in_use)
            workfile_state.output_tables[table_id] = new_grid(table_id, DEFAULT_TABLE_ROWS, DEFAULT_TABLE_COLUMNS)
            workfile_state.output_table_rows.append({
                "table_id": table_id, "table_name": name,
                "rows": str(DEFAULT_TABLE_ROWS), "columns": str(DEFAULT_TABLE_COLUMNS),
            })

            # Automatic Running Order placement -- no real
            # slide/position yet (that's for the user to sort out via this
            # tab's own Preview sandbox or the Running Order tab), but the
            # row exists from the moment the table does, rather than
            # requiring a manual Insert above/below via Preview first.
            page_w, page_h = get_page_size_emu(the_settings, None)
            append_content_row_above_footer(workfile_state.running_order_rows, {
                "function":       "insert_table",
                "table_id":       table_id,
                "table_type_ref": "plain_grid",
                "width_emu":      percent_to_emu(70.0, page_w, page_h),
                "height_emu":     percent_to_emu(50.0, page_w, page_h),
                "notes":          "Output Table",
            })

            workfile_state.dirty = True
            # "ot_table_choice" is a widget-bound key that's already been
            # instantiated earlier in this same run (the "Output Table"
            # selectbox above, in the shared "Select Table" box) -- can't be
            # written to directly here, same restriction as the Save to
            # Running Order success branch further down. Staged in the
            # existing "pending" key instead; applied at the top of
            # render_output_tables_tab, before that selectbox is created on
            # the next run.
            st.session_state["ot_pending_table_choice"] = name
            st.success(f"Created '{name}'.")
            st.rerun()
