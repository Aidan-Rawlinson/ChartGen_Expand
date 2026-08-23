"""
chart_store_area.py
The Chart Store table, shown in the right-hand content area in place of
the chart preview while "Show Chart Store" is toggled on. Read-only list;
delete, export and import only.
"""

import os

import pandas as pd
import streamlit as st

from chartgen.output_generation.execution.charts.chart_store_xlsx import (
    write_chart_store_xlsx, read_chart_store_xlsx, assign_missing_chart_store_ids,
)
from chartgen.shared.infrastructure.cg_extracts import get_extracts_folder
from chartgen.shared.infrastructure.page_sizing import emu_to_percent, get_page_size_emu
from chartgen.ui.common.pickers import pick_xlsx_file
from chartgen.ui.tabs.charts_tab.helpers import _int_or_none


def _render_chart_store_area(workfile_state, the_manifest, label_by_cache_file, the_settings):
    """
    The Chart Store table -- shown in the right-hand content area in place
    of the chart preview, never alongside it, while "Show Chart Store" is
    toggled on. Read-only list; delete, export and import only.
    """
    st.subheader("Chart Store")
    chart_store_rows = workfile_state.chart_store_rows

    if not chart_store_rows:
        st.caption("No Chart Store entries yet — use Save to Chart Store on a configured chart to add one.")
        return

    def _chart_label_for_cache_file(cache_file):
        entry = the_manifest.get(cache_file, {})
        title = str(entry.get("chart_title", "")).strip()
        ref = str(entry.get("chart_ref", "")).strip()
        if title and title != "...":
            return f"{ref or cache_file}  —  {title}"
        return ref or cache_file

    page_w, page_h = get_page_size_emu(the_settings, None)

    display_ids, display_types, display_sources, display_pops, display_sizes, display_descriptions = (
        [], [], [], [], [], []
    )
    for row in chart_store_rows:
        display_ids.append(row.get("chart_store_id", ""))
        display_types.append(row.get("base_chart_name", ""))
        display_sources.append(_chart_label_for_cache_file(row.get("cache_file", "")))
        display_pops.append(row.get("populations", "") or "(default)")
        w = _int_or_none(row.get("width_emu"))
        h = _int_or_none(row.get("height_emu"))
        w_pct = round(emu_to_percent(w, page_w, page_h), 1) if w else None
        h_pct = round(emu_to_percent(h, page_w, page_h), 1) if h else None
        display_sizes.append(f"{w_pct}% × {h_pct}%" if w_pct and h_pct else "—")
        display_descriptions.append(row.get("description", ""))

    selection = st.dataframe(
        pd.DataFrame({
            "ID": display_ids,
            "Chart type": display_types,
            "Data source": display_sources,
            "Populations": display_pops,
            "Size": display_sizes,
            "Description": display_descriptions,
        }),
        use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
    )
    selected_rows = selection.selection.get("rows", [])
    sel_idx = selected_rows[0] if selected_rows else None

    col_del, col_dl, col_ul = st.columns([1, 1, 1])

    if col_del.button("🗑  Delete selected entry", disabled=(sel_idx is None), use_container_width=True):
        del workfile_state.chart_store_rows[sel_idx]
        workfile_state.dirty = True
        st.rerun()

    extracts_dir = get_extracts_folder(workfile_state.workfile_path)

    if col_dl.button("⬇  Export Chart Store", use_container_width=True, key="cstore_export_btn"):
        export_path = os.path.join(extracts_dir, "chart_store.xlsx")
        write_chart_store_xlsx(chart_store_rows, export_path)
        st.success(f"Exported to {export_path}")

    if col_ul.button("⬆  Import Chart Store", use_container_width=True, key="cstore_import_btn"):
        picked_path = pick_xlsx_file(extracts_dir, "Select edited Chart Store Excel file")
        if picked_path:
            imported_rows = read_chart_store_xlsx(picked_path)
            workfile_state.chart_store_rows = assign_missing_chart_store_ids(imported_rows, workfile_state.settings)
            workfile_state.dirty = True
            st.rerun()
