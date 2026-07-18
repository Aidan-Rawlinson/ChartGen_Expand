"""
outputs_tab.py
Outputs tab — Run Selected / Run Batch / Run All, with a live run log.
"""

import os

import streamlit as st

from core.output_generation.execution.batch_process import run_batch
from core.ui.common.formatting import render_run_log_html
from core.ui.common.guidance import guidance_link_html
from core.workfile.state.session_state import ws, settings, save_settings, master_table


def render_outputs_tab():
    s           = settings()
    subs        = master_table()
    workfile_dir = os.path.dirname(ws().workfile_path)
    cleaned_tpl = s.get("cleaned_template_path", "").strip()
    tpl         = s.get("ppt_template_path", "").strip()
    active_tpl  = cleaned_tpl if os.path.exists(cleaned_tpl) else tpl
    sel_id      = str(s.get("selected_unit_id", "") or "").strip()
    sel_row     = next((r for r in subs if str(r["unit_id"]) == sel_id), None)
    total       = len(subs)
    cursor      = min(int(s.get("batch_cursor", 0)), total)
    outputs_dir = os.path.join(workfile_dir, "outputs")
    ro_rows     = ws().running_order_rows

    st.markdown('<h1 style="font-size:1.8em;margin:0 0 4px 0;padding:0;">Create Outputs' +
                guidance_link_html("outputs") + '</h1>'
                '<hr style="border:none;border-top:1px solid #ddd;margin:0 0 6px 0;">', unsafe_allow_html=True)

    issues = []
    if not active_tpl or not os.path.exists(active_tpl):
        issues.append("No PowerPoint template configured. Process one in the Imports tab.")
    if not ro_rows:
        issues.append("No Running Order found. Process a template in the Imports tab first.")

    enabled_rows = []
    if not issues:
        enabled_rows = [r for r in ro_rows if r["enabled"] == 1]
        if not enabled_rows:
            issues.append("Running Order has rows, but none are enabled. Enable rows in the Running Order tab.")
        unassigned = [r for r in enabled_rows if r["function"] == "insert_chart"
                      and not str(r.get("chart_type_ref", "")).strip()]
        if unassigned:
            issues.append(f"{len(unassigned)} insert_chart row(s) have no chart type assigned.")

    if issues:
        with st.expander("⚠  Setup issues", expanded=True):
            for iss in issues:
                st.warning(iss)

    can_run = not issues and bool(enabled_rows)

    def _run_for_units(units_to_run: list):
        all_rows = [r for r in ws().running_order_rows if r["enabled"] == 1]

        base_settings = dict(s)
        base_settings["cleaned_template_path"] = active_tpl
        base_settings["outputs_folder"] = outputs_dir
        base_settings["workfile_state"] = ws()

        if "run_log_rows" not in st.session_state:
            st.session_state["run_log_rows"] = []

        def _on_unit_complete(log_entry):
            st.session_state["run_log_rows"].append(log_entry)
            render_run_log_html(_log_placeholder, st.session_state["run_log_rows"])

        result = run_batch(
            all_rows, units_to_run, subs, base_settings,
            on_unit_complete=_on_unit_complete,
        )
        return result["ok_count"], result["err_count"], result["elapsed"]

    st.markdown("""<style>
    [data-testid="stSlider"] [data-testid="stThumbValue"] { display:none !important; }
    [data-testid="stSlider"] { padding-bottom:0 !important; margin-bottom:0 !important; }
    </style>""", unsafe_allow_html=True)

    if can_run:
        next_sub  = subs[cursor] if cursor < total else None
        remaining = total - cursor

        st.markdown('<p style="font-weight:600;font-size:0.88em;margin:0 0 2px 0;">Selected reporting unit</p>', unsafe_allow_html=True)
        r1l, r1r = st.columns([4, 2])
        with r1l:
            if sel_row:
                st.markdown(
                    f'<div style="border-left:4px solid #C12958;padding:4px 10px;background:#fdf0f3;border-radius:4px;line-height:1.35;display:inline-block;width:100%;">'
                    f'<span style="color:#C12958;font-weight:700;font-size:0.74em;letter-spacing:0.05em;">SELECTED REPORTING UNIT</span><br>'
                    f'<span style="font-size:0.92em;font-weight:600;">{sel_row["unit_name"]}</span><br>'
                    f'<span style="color:#555;font-size:0.8em;">{sel_row["unit_code"]}</span>'
                    f'</div>', unsafe_allow_html=True,
                )
            else:
                st.markdown('<p style="color:#888;font-size:0.83em;margin:4px 0;">No reporting unit selected — go to the Select tab.</p>', unsafe_allow_html=True)
        with r1r:
            run_selected = st.button(
                f"▶  Run Selected{(' — ' + sel_row['unit_code']) if sel_row else ''}",
                disabled=not sel_row, use_container_width=True, key="btn_run_selected", type="primary",
            )

        st.markdown('<hr style="border:none;border-top:1px solid #ddd;margin:4px 0;">', unsafe_allow_html=True)

        st.markdown('<p style="font-weight:600;font-size:0.88em;margin:0 0 2px 0;">Batch processing</p>', unsafe_allow_html=True)
        r2l, r2r = st.columns([4, 2])
        with r2l:
            if next_sub:
                st.markdown(f'<p style="font-size:0.81em;color:#444;margin:0;">Next: <strong>{next_sub["unit_name"]}</strong> ({next_sub["unit_code"]}) — {cursor + 1} of {total}</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p style="font-size:0.81em;color:#888;margin:0;">Queue complete — all {total} reports run.</p>', unsafe_allow_html=True)
            sl_col, rs_col = st.columns([3, 2])
            with sl_col:
                batch_size = st.slider("Batch size", min_value=1, max_value=min(50, max(remaining, 1)),
                    value=min(10, max(remaining, 1)), key="batch_size_slider", label_visibility="collapsed")
            with rs_col:
                if st.button("↺  Reset queue", key="btn_reset_queue"):
                    s["batch_cursor"] = "0"
                    save_settings(s)
                    st.session_state["run_log_rows"] = []
                    st.rerun()
        with r2r:
            run_batch_clicked = st.button(
                f"▶▶  Run Batch — next {min(batch_size, remaining)}",
                disabled=(cursor >= total), use_container_width=True, key="btn_run_batch", type="primary",
            )

        st.markdown('<hr style="border:none;border-top:1px solid #ddd;margin:4px 0;">', unsafe_allow_html=True)

        st.markdown('<p style="font-weight:600;font-size:0.88em;margin:0 0 2px 0;">Full run</p>', unsafe_allow_html=True)
        r3l, r3r = st.columns([4, 2])
        with r3l:
            st.markdown(f'<p style="font-size:0.81em;color:#444;margin:4px 0;">All <strong>{total}</strong> units in the population.</p>', unsafe_allow_html=True)
        with r3r:
            run_all_clicked = st.button(
                f"▶▶▶  Run All — {total} reports",
                use_container_width=True, key="btn_run_all", type="primary",
            )

        st.divider()

        if "run_log_rows" not in st.session_state:
            st.session_state["run_log_rows"] = []
        _log_placeholder = st.empty()

        if run_selected and sel_row:
            _run_for_units([sel_row])

        elif run_batch_clicked and cursor < total:
            batch_subs = subs[cursor: cursor + batch_size]
            ok, err, elapsed = _run_for_units(batch_subs)
            s["batch_cursor"] = str(cursor + ok)
            save_settings(s)
            st.rerun()

        elif run_all_clicked:
            ok, err, elapsed = _run_for_units(subs)
            s["batch_cursor"] = str(ok)
            save_settings(s)
            st.rerun()

        if st.session_state.get("run_log_rows"):
            render_run_log_html(_log_placeholder, st.session_state["run_log_rows"])
