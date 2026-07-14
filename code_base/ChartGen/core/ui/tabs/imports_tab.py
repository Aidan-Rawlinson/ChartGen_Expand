"""
imports_tab.py
Imports tab — PowerPoint template upload/processing and toolkit API fetch.

The template -> extract URLs -> fetch -> generate Running Order sequence is
delegated to core.acquisition.import_flow.process_template; this tab only
collects the upload, shows progress, and displays the result. See
Restructure_Plan.md Open Item 3.
"""

import os
import tempfile

import streamlit as st

from core.acquisition.import_flow import process_template
from core.acquisition.toolkit_nhs.fetch import fetch_all
from core.workfile.state.session_state import ws, settings, save_settings, manifest


def render_imports_tab():
    st.header("Import Project Data")
    st.subheader("PowerPoint Template")

    s = settings()
    current_ppt_path    = s.get("ppt_template_path", "")
    current_cleaned_path = s.get("cleaned_template_path", "")

    if current_ppt_path:
        st.caption(f"Template: `{current_ppt_path}`")
    if current_cleaned_path:
        st.caption(f"Cleaned template: `{current_cleaned_path}`")

    uploaded_template = st.file_uploader(
        "Upload PowerPoint template (.pptx)", type=["pptx"],
        key="ppt_template_uploader",
        help="Named chart placeholders are read automatically. "
             "Yellow textboxes containing toolkit URLs are extracted and stripped.",
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

            progress_bar = st.progress(0)
            status_text = st.empty()

            def _on_fetch_progress(current, total, label):
                progress_bar.progress(current / total)
                status_text.text(f"Fetching {current}/{total}: {label}")

            try:
                with st.spinner("Processing template — reading, fetching data, building Running Order…"):
                    result = process_template(
                        tmp_path, cleaned_path,
                        workfile_state=ws_cur,
                        token=st.session_state["token"],
                        on_fetch_progress=_on_fetch_progress,
                    )
            except Exception as e:
                st.error(f"Template processing failed: {e}")
                os.unlink(tmp_path)
                st.stop()
            finally:
                status_text.empty()
                progress_bar.empty()
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
                st.info(
                    f"urls — {result['new_urls_added']} new URL(s) added, "
                    f"{result['new_urls_already_present']} already present."
                )
                fetch_results = result["fetch_results"]
                ok  = [r for r in fetch_results if r["status"] == "ok"]
                err = [r for r in fetch_results if r["status"] != "ok"]
                st.success(f"Data fetch complete — {len(ok)} succeeded, {len(err)} failed.")
                for r in err:
                    st.error(f"✗ [{r['tier_id']}] {r['label']} — {r['message']}")
            else:
                st.info("No URLs found in template. Skipping data fetch.")

            st.success(f"Running Order generated — {len(result['running_order_rows'])} rows.")
            st.session_state["template_result"] = template_result

    st.divider()
    st.subheader("Toolkit API — Fetch Chart Data")
    if st.button("Fetch All Chart Data"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def on_progress(current, total, label):
            progress_bar.progress(current / total)
            status_text.text(f"Fetching {current}/{total}: {label}")

        with st.spinner("Fetching data…"):
            fetch_results = fetch_all(
                st.session_state["token"],
                on_progress=on_progress,
                workfile_state=ws(),
            )
        status_text.empty()
        progress_bar.empty()

        for r in fetch_results:
            if r["status"] == "ok":
                st.success(f"✓ [{r['tier_id']}] {r['label']} — {r['message']}")
            else:
                st.error(f"✗ [{r['tier_id']}] {r['label']} — {r['message']}")
