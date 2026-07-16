"""
populations_tab.py
Populations tab — every population-level table currently in the workfile,
with controls to reorder them. Whichever table sits on top is the master
table, driving reporting unit selection (Reporting unit selection tab) and
the batch loop.
"""

import streamlit as st

from core.ui.common.formatting import population_table_columns, display_column_labels
from core.workfile.state.session_state import ws


def render_populations_tab():
    st.header("Populations")
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

        if i < len(table_order) - 1:
            st.divider()
