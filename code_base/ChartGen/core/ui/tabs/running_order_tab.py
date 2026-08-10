"""
running_order_tab.py
Running Order tab — master/detail view of the Running Order, with an edit
dialog per row.

Chart-type filtering by data shape and populations-string build/parse are
delegated to core.output_generation.definition.running_order — this dialog
only renders the widgets and applies the user's selection back to the row.
"""

import os

import streamlit as st

from core.acquisition.toolkit_nhs.peer_groups import get_peer_group_value_options
from core.output_generation.definition.running_order import (
    read_xlsx, write_xlsx,
    get_valid_chart_refs_for_cache_file,
    build_populations_options, parse_populations_string, build_populations_string,
)
from core.output_generation.execution.charts.cache_reader import periods_for_cache_file
from core.output_generation.execution.pptx_com.position_finder import get_selected_shape_position
from core.shared.infrastructure.cg_extracts import get_extracts_folder
from core.ui.common.guidance import render_tab_header
from core.ui.common.pickers import pick_xlsx_file
from core.workfile.state.session_state import ws, manifest, master_table


def _render_position_finder():
    """
    Position Finder -- a Running Order support tool, not a Running Order
    row/function itself (see position_finder.py). Lives directly under
    the Running Order's own content on this tab, since it exists to
    support authoring Running Order rows, but sits outside the Running
    Order structure proper -- no row_id, not part of read_xlsx/write_xlsx,
    not executed by run_running_order.
    """
    with st.expander("Position Finder"):
        st.caption(
            "Select a chart or link icon on the currently open PowerPoint "
            "slide, then press the button below to read its live position "
            "and size -- for copying into a Running Order row by hand."
        )
        if st.button("Get selected shape's position", key="position_finder_button"):
            result = get_selected_shape_position()
            if result["status"] == "error":
                st.warning(result["message"])
            elif result["kind"] == "chart_or_other":
                st.caption(f"Shape: **{result['name'] or '(unnamed)'}**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Left EMU",   result["left_emu"])
                c2.metric("Top EMU",    result["top_emu"])
                c3.metric("Width EMU",  result["width_emu"])
                c4.metric("Height EMU", result["height_emu"])
            elif result["kind"] == "link_without_chart":
                st.caption(f"Shape: **{result['name']}**")
                st.info(result["note"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Left EMU",   result["left_emu"])
                c2.metric("Top EMU",    result["top_emu"])
                c3.metric("Width EMU",  result["width_emu"])
                c4.metric("Height EMU", result["height_emu"])
            elif result["kind"] == "link_with_chart":
                st.caption(f"Shape: **{result['name']}**  ·  matched to **{result['matched_chart_name']}**")
                st.markdown("**As hyperlink_left / hyperlink_top / hyperlink_size** (offsets from the matched chart's own top-right corner):")
                c1, c2, c3 = st.columns(3)
                c1.metric("hyperlink_left",  result["hyperlink_left_emu"])
                c2.metric("hyperlink_top",   result["hyperlink_top_emu"])
                c3.metric("hyperlink_size",  result["hyperlink_size_emu"])
                with st.expander("Icon's own absolute position (if the offset above isn't what you need)"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Left EMU",   result["left_emu"])
                    c2.metric("Top EMU",    result["top_emu"])
                    c3.metric("Width EMU",  result["width_emu"])
                    c4.metric("Height EMU", result["height_emu"])


def render_running_order_tab():
    render_tab_header("Running Order", "running_order")

    ws_ro = ws()
    if not ws_ro.running_order_rows:
        st.info("No Running Order found. Upload and process a PowerPoint template in the Imports tab.")
        _render_position_finder()
        return

    try:
        import pandas as pd

        the_manifest = manifest()
        cache_to_label = {}
        for fname, entry in the_manifest.items():
            _title = str(entry.get("chart_title", "")).strip()
            _ref   = str(entry.get("chart_ref", "")).strip()
            cache_to_label[fname] = (f"{_ref}: {_title}" if (_title and _title != "...")
                                     else (_ref or fname))

        rows = ws_ro.running_order_rows

        @st.dialog("Edit row", width="large")
        def _row_edit_dialog(sel_idx):
            row  = ws_ro.running_order_rows[sel_idx]
            func = str(row.get("function", ""))
            is_insert_chart    = func == "insert_chart"
            is_set_default_pop = func == "set_default_populations"
            is_content         = func in {"insert_chart", "empty_placeholder"}
            needs_populations  = is_insert_chart or is_set_default_pop

            st.caption(f"Row {row['row_id']}  ·  {func}")
            if is_content:
                st.caption(f"Slide: **{row.get('slide_index', '')}**")

            f_enabled = st.checkbox("Enabled", value=(row.get("enabled", 1) == 1))
            f_notes   = st.text_input("Notes", value=str(row.get("notes", "") or ""))

            if is_insert_chart:
                cache_file = str(row.get("cache_file", "") or "")
                converts_to_metrics = bool(str(row.get("metric_periods", "") or "").strip())
                valid_refs = get_valid_chart_refs_for_cache_file(
                    cache_file, the_manifest, converts_to_metrics, custom_chart_rows=ws_ro.custom_chart_rows
                )
                shape_type = the_manifest.get(cache_file, {}).get("shape_type", "")
                label_hint = cache_to_label.get(cache_file, cache_file)
                shape_hint = f"  ·  {shape_type}" if shape_type else ""
                st.caption(f"Data: {label_hint}{shape_hint}")

                current_ref = str(row.get("base_chart_name", "") or "")
                ref_options = [""] + valid_refs
                try:
                    ref_index = ref_options.index(current_ref)
                except ValueError:
                    ref_index = 0

                f_chart_type = st.selectbox(
                    "Chart type", options=ref_options, index=ref_index,
                    format_func=lambda v: "— select chart type —" if v == "" else v,
                )
                with st.expander("Position & size"):
                    pc1, pc2, pc3, pc4 = st.columns(4)
                    pc1.metric("Left EMU",   row.get("left_emu",   ""))
                    pc2.metric("Top EMU",    row.get("top_emu",    ""))
                    pc3.metric("Width EMU",  row.get("width_emu",  ""))
                    pc4.metric("Height EMU", row.get("height_emu", ""))
            else:
                f_chart_type = row.get("base_chart_name", "")

            if needs_populations:
                peer_options = get_peer_group_value_options(master_table())
                pop_options = build_populations_options(peer_options)
                current_pop_str = str(row.get("populations", "") or "")
                if is_insert_chart and not current_pop_str:
                    current_pop_list = []
                    pop_help = "Leave blank to inherit the default populations set above."
                else:
                    current_pop_list = parse_populations_string(current_pop_str, pop_options)
                    pop_help = "Order is fixed: All → peer groups → Selected."

                f_populations_selected = st.multiselect(
                    "Populations" + (" (override — blank = use default)" if is_insert_chart else ""),
                    options=pop_options, default=current_pop_list, help=pop_help,
                )
                f_populations = build_populations_string(f_populations_selected, pop_options)
            else:
                f_populations = str(row.get("populations", "") or "")

            st.divider()
            col_apply, col_cancel = st.columns([1, 1])

            if col_apply.button("Apply", type="primary"):
                ws_ro.running_order_rows[sel_idx]["enabled"] = 1 if f_enabled else 0
                ws_ro.running_order_rows[sel_idx]["notes"]   = f_notes
                if is_insert_chart:
                    ws_ro.running_order_rows[sel_idx]["base_chart_name"] = f_chart_type
                if needs_populations:
                    ws_ro.running_order_rows[sel_idx]["populations"] = f_populations
                ws_ro.dirty = True
                st.session_state["ro_selected_idx"] = None
                st.rerun()

            if col_cancel.button("Cancel"):
                st.session_state["ro_selected_idx"] = None
                st.rerun()

        if not rows:
            st.info("Running Order is empty.")
            return

        def _short_func(f):
            return {
                "create_ppt":              "▶  create_ppt",
                "set_default_populations": "◉  set_default_populations",
                "save_ppt":                "■  save_ppt",
                "save_pdf":                "■  save_pdf",
                "insert_chart":            "◈  insert_chart",
                "empty_placeholder":       "○  empty_placeholder",
                "update_text":             "✎  update_text",
            }.get(f, f)

        overview_df = pd.DataFrame({
            "#":           [r["row_id"] for r in rows],
            "On":          ["✓" if r["enabled"] == 1 else "–" for r in rows],
            "Function":    [_short_func(str(r.get("function", ""))) for r in rows],
            "Slide":       [r.get("slide_index", "") for r in rows],
            "Chart type":  [r.get("base_chart_name", "") for r in rows],
            "Notes":       [r.get("notes", "") for r in rows],
        })

        selection = st.dataframe(
            overview_df, use_container_width=True, hide_index=True,
            height=min(36 * len(rows) + 38, 540),
            on_select="rerun", selection_mode="single-row",
            column_config={
                "#":     st.column_config.Column(width="small"),
                "On":    st.column_config.Column(width="small"),
                "Slide": st.column_config.Column(width="small"),
            },
        )
        selected_rows = selection.selection.get("rows", [])
        st.session_state["ro_selected_idx"] = selected_rows[0] if selected_rows else None
        sel_idx = st.session_state["ro_selected_idx"]

        col_edit, col_dl, col_ul = st.columns([1, 1, 1])

        edit_label = (
            f"✎  Edit row {rows[sel_idx]['row_id']}" if sel_idx is not None else "✎  Edit row"
        )
        edit_clicked = col_edit.button(
            edit_label, disabled=(sel_idx is None), type="secondary", use_container_width=True,
        )

        # Only cache files actually referenced by an insert_chart row need
        # a period list — built once per export rather than for every
        # cached file in the workfile.
        periods_by_cache_file = {}
        for r in rows:
            if str(r.get("function", "")) == "insert_chart":
                cf = str(r.get("cache_file") or "").strip()
                if cf and cf not in periods_by_cache_file:
                    periods_by_cache_file[cf] = periods_for_cache_file(cf, ws_ro)

        extracts_dir = get_extracts_folder(ws_ro.workfile_path)

        if col_dl.button("⬇  Export Running Order", use_container_width=True, key="ro_export_btn"):
            export_path = os.path.join(extracts_dir, "running_order.xlsx")
            write_xlsx(rows, export_path, manifest=the_manifest, periods_by_cache_file=periods_by_cache_file,
                      custom_chart_rows=ws_ro.custom_chart_rows)
            st.success(f"Exported to {export_path}")

        if col_ul.button("⬆  Import Running Order", use_container_width=True, key="ro_import_btn"):
            picked_path = pick_xlsx_file(extracts_dir, "Select edited Running Order Excel file")
            if picked_path:
                ws_ro.running_order_rows = read_xlsx(picked_path)
                ws_ro.dirty = True
                st.rerun()

        if edit_clicked and sel_idx is not None:
            _row_edit_dialog(sel_idx)

        _render_position_finder()

    except ImportError:
        st.warning("Install openpyxl and pandas to use the Running Order editor.")
    except Exception as e:
        st.error(f"Could not load Running Order: {e}")
