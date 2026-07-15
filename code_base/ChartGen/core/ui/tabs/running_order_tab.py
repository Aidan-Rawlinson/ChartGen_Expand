"""
running_order_tab.py
Running Order tab — master/detail view of the Running Order, with an edit
dialog per row.

Chart-type filtering by data shape and populations-string build/parse are
delegated to core.output_generation.definition.running_order — this dialog
only renders the widgets and applies the user's selection back to the row.
"""

import io

import streamlit as st

from core.acquisition.toolkit_nhs.peer_groups import get_peer_group_value_options
from core.output_generation.definition.running_order import (
    read_xlsx, write_xlsx,
    get_valid_chart_refs_for_cache_file,
    build_populations_options, parse_populations_string, build_populations_string,
)
from core.workfile.state.session_state import ws, manifest, units


def render_running_order_tab():
    st.header("Running Order")

    ws_ro = ws()
    if not ws_ro.running_order_rows:
        st.info("No Running Order found. Upload and process a PowerPoint template in the Imports tab.")
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
                st.caption(f"Placeholder: **{row.get('placeholder', '')}**  ·  Slide: **{row.get('slide_index', '')}**")

            f_enabled = st.checkbox("Enabled", value=(row.get("enabled", 1) == 1))
            f_notes   = st.text_input("Notes", value=str(row.get("notes", "") or ""))

            if is_insert_chart:
                cache_file = str(row.get("cache_file", "") or "")
                valid_refs = get_valid_chart_refs_for_cache_file(cache_file, the_manifest)
                shape_type = the_manifest.get(cache_file, {}).get("shape_type", "")
                label_hint = cache_to_label.get(cache_file, cache_file)
                shape_hint = f"  ·  {shape_type}" if shape_type else ""
                st.caption(f"Data: {label_hint}{shape_hint}")

                current_ref = str(row.get("chart_type_ref", "") or "")
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
                f_chart_type = row.get("chart_type_ref", "")

            if needs_populations:
                peer_options = get_peer_group_value_options(units())
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
                    ws_ro.running_order_rows[sel_idx]["chart_type_ref"] = f_chart_type
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
            "Placeholder": [r.get("placeholder", "") for r in rows],
            "Chart type":  [r.get("chart_type_ref", "") for r in rows],
            "Notes":       [r.get("notes", "") for r in rows],
        })

        selection = st.dataframe(
            overview_df, use_container_width=True, hide_index=True,
            height=min(36 * len(rows) + 38, 540),
            on_select="rerun", selection_mode="single-row",
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

        ro_buffer = io.BytesIO()
        write_xlsx(rows, ro_buffer, manifest=the_manifest)
        col_dl.download_button(
            label="⬇  Download Running Order", data=ro_buffer.getvalue(),
            file_name="running_order.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        if col_ul.button("⬆  Upload Running Order", use_container_width=True):
            st.session_state["ro_show_uploader"] = not st.session_state.get("ro_show_uploader", False)

        if st.session_state.get("ro_show_uploader", False):
            uploaded_ro = st.file_uploader(
                "Upload Running Order", type=["xlsx"], key="ro_uploader",
                label_visibility="collapsed",
            )
            if uploaded_ro is not None:
                ws_ro.running_order_rows = read_xlsx(io.BytesIO(uploaded_ro.getbuffer()))
                ws_ro.dirty = True
                st.session_state["ro_show_uploader"] = False
                st.rerun()

        if edit_clicked and sel_idx is not None:
            _row_edit_dialog(sel_idx)

    except ImportError:
        st.warning("Install openpyxl and pandas to use the Running Order editor.")
    except Exception as e:
        st.error(f"Could not load Running Order: {e}")
