"""
imports_tab.py
Imports tab — PowerPoint template upload/processing, the chart URL
(manifest) table (read-only display with Excel round-trip for editing), and
the single data fetch.

Template processing populates the manifest table only (no fetch); the Fetch
button below the table is the one place data is pulled. Table editing is
via the Excel download/upload route only, through
manifest_table.apply_manifest_import.
"""

import io
import os
import tempfile

import streamlit as st

from core.acquisition.import_flow import process_template
from core.acquisition.fetch_dispatch import fetch_all
from core.acquisition.manifest_table import (
    write_manifest_xlsx, read_manifest_xlsx, apply_manifest_import,
)
from core.ui.common.guidance import render_tab_header
from core.workfile.state.session_state import ws, settings, save_settings

TABLE_COLUMNS = [
    "chart_ref", "hex_id", "url", "chart_title", "database",
    "project_id", "service_id", "year", "shape_type", "source",
    "data_updated_at",
]


def render_imports_tab():
    render_tab_header("Import Project Data", "imports")

    _render_template_section()
    st.divider()
    _render_url_table_section()
    st.divider()
    _render_fetch_section()


# ---------------------------------------------------------------------------
# PowerPoint template
# ---------------------------------------------------------------------------

def _render_template_section():
    st.subheader("PowerPoint Template")

    s = settings()
    current_ppt_path     = s.get("ppt_template_path", "")
    current_cleaned_path = s.get("cleaned_template_path", "")

    if current_ppt_path:
        st.caption(f"Template: `{current_ppt_path}`")
    if current_cleaned_path:
        st.caption(f"Cleaned template: `{current_cleaned_path}`")

    uploaded_template = st.file_uploader(
        "Upload PowerPoint template (.pptx)", type=["pptx"],
        key="ppt_template_uploader",
        help="Named chart placeholders are read automatically. "
             "Yellow textboxes containing toolkit URLs are extracted into the "
             "chart URL table below and stripped. No data is fetched at this "
             "point — use Fetch All Chart Data once the table is ready.",
    )

    if uploaded_template is not None:
        if st.button("Process Template"):
            ws_cur = ws()
            workfile_dir = os.path.dirname(ws_cur.workfile_path)
            workfile_name = ws_cur.workfile_name or "template"
            cleaned_path = os.path.join(workfile_dir, f"{workfile_name}.pptx")

            raw_bytes = uploaded_template.getbuffer()
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name

            try:
                with st.spinner("Processing template — reading placeholders, building Running Order…"):
                    result = process_template(
                        tmp_path, cleaned_path,
                        workfile_state=ws_cur,
                    )
            except Exception as e:
                st.error(f"Template processing failed: {e}")
                os.unlink(tmp_path)
                st.stop()
            os.unlink(tmp_path)

            s = settings()
            s["cleaned_template_path"] = cleaned_path
            s["ppt_template_path"] = cleaned_path
            save_settings(s)

            template_result = result["template_result"]
            with_url = [p for p in template_result.placeholders if p.url]
            without_url = [p for p in template_result.placeholders if not p.url]
            st.success(
                f"Template read — {len(template_result.placeholders)} placeholder(s): "
                f"{len(with_url)} with URL, {len(without_url)} empty."
            )
            if template_result.warnings:
                for w in template_result.warnings:
                    st.warning(w)

            if with_url:
                parts = [f"{result['new_urls_added']} new URL(s) added"]
                if result["urls_resurrected"]:
                    parts.append(f"{result['urls_resurrected']} restored")
                parts.append(f"{result['new_urls_already_present']} already present")
                st.info("Chart URL table — " + ", ".join(parts) + ".")
            else:
                st.info("No URLs found in template.")

            st.success(f"Running Order generated — {len(result['running_order_rows'])} rows.")
            st.session_state["template_result"] = template_result


# ---------------------------------------------------------------------------
# Chart URL (manifest) table
# ---------------------------------------------------------------------------

def _render_url_table_section():
    st.subheader("Chart URLs")
    ws_cur = ws()

    # Flash message from the previous run's table/Excel merge (set before rerun)
    flash = st.session_state.pop("manifest_merge_result", None)
    if flash:
        _report_merge_result(flash)

    live_rows = [r for r in ws_cur.manifest_rows
                 if str(r.get("deleted", "0")) != "1"]

    display_rows = [{c: r.get(c, "") for c in TABLE_COLUMNS} for r in live_rows]

    st.dataframe(
        display_rows,
        use_container_width=True,
        column_config={
            "chart_ref":       st.column_config.TextColumn("Chart"),
            "hex_id":          st.column_config.TextColumn("ID"),
            "url":             st.column_config.TextColumn("URL", width="large"),
            "chart_title":     st.column_config.TextColumn("Title"),
            "database":        st.column_config.TextColumn("Database"),
            "project_id":      st.column_config.TextColumn("Project"),
            "service_id":      st.column_config.TextColumn("Service"),
            "year":            st.column_config.TextColumn("Year"),
            "shape_type":      st.column_config.TextColumn("Data Shape"),
            "source":          st.column_config.TextColumn("Source"),
            "data_updated_at": st.column_config.TextColumn("Data Updated"),
        },
    )

    st.caption("Add or remove charts via the Excel download/upload below — "
               "download, edit (add a row with just a URL to add a chart; "
               "delete a row to remove its chart), and upload. Cached data "
               "for removed charts is retained. System columns are populated "
               "at fetch.")

    # --- Excel round-trip ---
    col_dl, col_ul = st.columns(2)

    with col_dl:
        xlsx_buffer = io.BytesIO()
        write_manifest_xlsx(ws_cur.manifest_rows, xlsx_buffer)
        st.download_button(
            "⬇  Download as Excel",
            data=xlsx_buffer.getvalue(),
            file_name=f"{ws_cur.workfile_name or 'chartgen'}_chart_urls.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_ul:
        if st.button("⬆  Upload edited Excel", use_container_width=True):
            st.session_state["manifest_show_uploader"] = not st.session_state.get("manifest_show_uploader", False)

    if st.session_state.get("manifest_show_uploader", False):
        uploaded_xlsx = st.file_uploader(
            "Upload edited Excel", type=["xlsx"], key="manifest_xlsx_uploader",
            label_visibility="collapsed",
        )
        if uploaded_xlsx is not None:
            try:
                imported = read_manifest_xlsx(io.BytesIO(uploaded_xlsx.getbuffer()))
                result = apply_manifest_import(imported, workfile_state=ws_cur)
            except Exception as e:
                st.error(f"Excel import failed: {e}")
                st.stop()
            st.session_state["manifest_merge_result"] = result
            st.session_state["manifest_show_uploader"] = False
            st.rerun()


def _report_merge_result(result: dict):
    parts = []
    if result["added"]:
        parts.append(f"{result['added']} added")
    if result["updated"]:
        parts.append(f"{result['updated']} updated")
    if result["deleted"]:
        parts.append(f"{result['deleted']} removed")
    st.success("Chart URL table updated — " + (", ".join(parts) if parts else "no changes") + ".")
    if result["unknown_hex_ids"]:
        st.warning("Unrecognised ID(s) skipped: " + ", ".join(result["unknown_hex_ids"]))


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _render_fetch_section():
    st.subheader("Toolkit API — Fetch Chart Data")
    st.caption("Full refresh of every chart in the table above.")

    # Flash message from the previous run's fetch (set before rerun) — same
    # pattern as manifest_merge_result above. Without the rerun, tabs that
    # render earlier in app.py's script order (Populations, Select) would
    # keep showing pre-fetch state even though the fetch already completed,
    # since st.tabs() draws every tab once per run, not on tab switch.
    flash = st.session_state.pop("fetch_results_flash", None)
    if flash:
        for r in flash:
            if r["status"] == "ok":
                st.success(f"✓ [{r['hex_id']}] {r['label']} — {r['message']}")
            elif r["status"] == "warning":
                st.warning(f"⚠ {r['label']} — {r['message']}")
            else:
                st.error(f"✗ [{r['hex_id']}] {r['label']} — {r['message']}")

    if st.button("Fetch All Chart Data"):
        token = st.session_state.get("token")
        if not token:
            st.error(
                "No valid session credentials — please sign out and sign in again."
            )
            st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()

        def on_progress(current, total, label):
            progress_bar.progress(current / total)
            status_text.text(f"Fetching {current}/{total}: {label}")

        with st.spinner("Fetching data…"):
            fetch_results = fetch_all(
                token,
                on_progress=on_progress,
                workfile_state=ws(),
            )
        status_text.empty()
        progress_bar.empty()

        st.session_state["fetch_results_flash"] = fetch_results
        st.rerun()
