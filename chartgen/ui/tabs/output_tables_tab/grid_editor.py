"""
grid_editor.py
Edit Grid mode: content authoring for the selected Output Table -- the
raw c0..cN grid, resize, Update, and the Excel round-trip.
"""

import os

import pandas as pd
import streamlit as st

from chartgen.output_generation.execution.tables.grid_store import resize_grid, validate_grid
from chartgen.output_generation.execution.tables.grid_xlsx import (
    write_output_table_xlsx, read_output_table_xlsx,
)
from chartgen.shared.infrastructure.cg_extracts import get_extracts_folder
from chartgen.ui.common.pickers import pick_xlsx_file


# ---------------------------------------------------------------------------
# Edit Grid mode -- content authoring for the selected Output Table
# ---------------------------------------------------------------------------

def _render_grid_editor(workfile_state, table_id, grid_rows):
    with st.expander("Resize grid", expanded=False):
        n_rows = max(0, len(grid_rows) - 1)
        n_cols = max(0, len(grid_rows[0]) - 1) if grid_rows else 0
        col_a, col_b = st.columns(2)
        with col_a:
            new_n_rows = st.number_input(
                "Rows", min_value=1, max_value=200, value=n_rows, step=1, key="ot_resize_rows",
            )
        with col_b:
            new_n_cols = st.number_input(
                "Columns", min_value=1, max_value=200, value=n_cols, step=1, key="ot_resize_cols",
            )
        if st.button("Apply resize", key="ot_apply_resize_btn"):
            resized = resize_grid(grid_rows, int(new_n_rows), int(new_n_cols), table_id)
            workfile_state.output_tables[table_id] = resized
            for idx_row in workfile_state.output_table_rows:
                if idx_row["table_id"] == table_id:
                    idx_row["rows"] = str(int(new_n_rows))
                    idx_row["columns"] = str(int(new_n_cols))
                    break
            workfile_state.dirty = True
            st.success("Grid resized.")
            st.rerun()

    df = pd.DataFrame(grid_rows)
    edited_df = st.data_editor(df, use_container_width=True, key=f"ot_grid_editor_{table_id}")

    col_update, col_dl, col_ul = st.columns([1, 1, 1])

    update_clicked = col_update.button(
        "Update", type="primary", use_container_width=True, key=f"ot_grid_update_{table_id}",
    )
    if update_clicked:
        new_grid_rows = edited_df.astype(str).to_dict(orient="records")
        warnings = validate_grid(new_grid_rows)
        workfile_state.output_tables[table_id] = new_grid_rows
        workfile_state.dirty = True
        if warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.success("Grid updated.")

    extracts_dir = get_extracts_folder(workfile_state.workfile_path)

    if col_dl.button(
        "\u2b07  Export to CG_Extracts", use_container_width=True, key=f"ot_grid_export_{table_id}",
    ):
        export_path = os.path.join(extracts_dir, f"{table_id}_grid.xlsx")
        write_output_table_xlsx(grid_rows, workfile_state.text_stats_rows, export_path)
        st.success(f"Exported to {export_path}")

    if col_ul.button(
        "\u2b06  Import from CG_Extracts", use_container_width=True, key=f"ot_grid_import_{table_id}",
    ):
        picked_path = pick_xlsx_file(extracts_dir, "Select edited grid Excel file")
        if picked_path:
            try:
                imported_grid = read_output_table_xlsx(picked_path)
            except Exception as e:
                st.error(f"Excel import failed: {e}")
                st.stop()
            workfile_state.output_tables[table_id] = imported_grid
            n_rows, n_cols = max(0, len(imported_grid) - 1), (max(0, len(imported_grid[0]) - 1) if imported_grid else 0)
            for idx_row in workfile_state.output_table_rows:
                if idx_row["table_id"] == table_id:
                    idx_row["rows"] = str(n_rows)
                    idx_row["columns"] = str(n_cols)
                    break
            workfile_state.dirty = True
            warnings = validate_grid(imported_grid)
            st.session_state["ot_grid_import_warnings"] = warnings
            st.rerun()

    import_warnings = st.session_state.pop("ot_grid_import_warnings", None)
    if import_warnings:
        for w in import_warnings:
            st.warning(w)
