"""
populations_tab.py
Populations tab — every population-level table currently in the workfile,
with controls to reorder them. Whichever table sits on top is the master
table, driving reporting unit selection (Reporting unit selection tab) and
the batch loop.

Each table also gets an Excel download/upload round-trip, identical in
pattern to the chart URL (manifest) table on the Imports tab — download,
edit (change unit_code/unit_name/soft_parents/peer columns, delete a row to
remove that unit, add a row with a new unit_id to add one), and upload. See
core.shared.infrastructure.population_table_xlsx for import semantics.
"""

import io

import streamlit as st

from core.ui.common.formatting import population_table_columns, display_column_labels
from core.ui.common.guidance import render_tab_header
from core.workfile.state.session_state import ws
from core.shared.infrastructure.population_table_xlsx import (
    write_population_table_xlsx, read_population_table_xlsx, apply_population_table_import,
)


def render_populations_tab():
    render_tab_header("Populations", "populations")
    st.caption("This sheet contains the populations we wish to compare in our analysis, charts, and tables.")
    st.divider()

    workfile_state = ws()
    table_order = workfile_state.table_order
    tables = workfile_state.tables

    if not table_order:
        st.info("No population tables loaded.")
        return

    import pandas as pd

    for i, table_name in enumerate(table_order):
        rows = tables.get(table_name, [])
        is_master = (i == 0)

        # Flash message from this table's previous Excel import (set before rerun)
        flash = st.session_state.pop(f"pop_table_import_result_{table_name}", None)
        if flash:
            _report_import_result(flash)

        header_col, up_col, down_col = st.columns([8, 1, 1])
        badge_html = (
            '<span style="margin-left:10px;color:#1a56db;font-weight:700;font-size:0.7rem;">'
            '★ MASTER — drives reporting unit selection</span>'
        ) if is_master else ""
        header_col.markdown(
            f'<span style="font-size:1.0rem;font-weight:700;">{table_name}</span>{badge_html}',
            unsafe_allow_html=True,
        )
        if up_col.button("▲", key=f"tbl_up_{table_name}", disabled=(i == 0),
                          use_container_width=True, help="Move up"):
            table_order[i - 1], table_order[i] = table_order[i], table_order[i - 1]
            workfile_state.dirty = True
            st.rerun()
        if down_col.button("▼", key=f"tbl_down_{table_name}", disabled=(i == len(table_order) - 1),
                            use_container_width=True, help="Move down"):
            table_order[i + 1], table_order[i] = table_order[i], table_order[i + 1]
            workfile_state.dirty = True
            st.rerun()

        with st.expander("Show rows", expanded=False, key=f"tbl_show_rows_{table_name}"):
            if not rows:
                st.info("No rows.")
            else:
                cols = population_table_columns(rows)
                df = pd.DataFrame(rows)[cols]
                df.columns = display_column_labels(cols)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"{len(rows)} row(s)")

            col_dl, col_ul = st.columns(2)

            with col_dl:
                xlsx_buffer = io.BytesIO()
                write_population_table_xlsx(table_name, rows, xlsx_buffer)
                st.download_button(
                    "⬇  Download as Excel",
                    data=xlsx_buffer.getvalue(),
                    file_name=f"{table_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"tbl_download_{table_name}",
                )

            with col_ul:
                uploader_flag = f"pop_show_uploader_{table_name}"
                if st.button("⬆  Upload edited Excel", use_container_width=True, key=f"tbl_upload_btn_{table_name}"):
                    st.session_state[uploader_flag] = not st.session_state.get(uploader_flag, False)

            if st.session_state.get(f"pop_show_uploader_{table_name}", False):
                uploaded_xlsx = st.file_uploader(
                    "Upload edited Excel", type=["xlsx"], key=f"pop_xlsx_uploader_{table_name}",
                    label_visibility="collapsed",
                )
                if uploaded_xlsx is not None:
                    try:
                        imported = read_population_table_xlsx(io.BytesIO(uploaded_xlsx.getbuffer()))
                        result = apply_population_table_import(table_name, imported, workfile_state=workfile_state)
                    except Exception as e:
                        st.error(f"Excel import failed: {e}")
                        st.stop()
                    st.session_state[f"pop_table_import_result_{table_name}"] = result
                    st.session_state[f"pop_show_uploader_{table_name}"] = False
                    st.rerun()

        if i < len(table_order) - 1:
            st.divider()


def _report_import_result(result: dict):
    parts = []
    if result["added"]:
        parts.append(f"{result['added']} added")
    if result["updated"]:
        parts.append(f"{result['updated']} updated")
    if result["deleted"]:
        parts.append(f"{result['deleted']} removed")
    st.success("Table updated — " + (", ".join(parts) if parts else "no changes") + ".")
    if result["skipped_blank_id"]:
        st.warning(f"{result['skipped_blank_id']} row(s) skipped — no unit ID given.")
