"""
new_workfile_form.py
UI for the New Workfile flow: a short description ("what is this workfile
for?", shown in the app header for as long as the workfile is open) plus a
single native Save dialog for name and location. Calls create_new_workfile —
a genuinely blank .cgw, no project, no population tables. This module owns
no business logic itself.
"""

import os

import streamlit as st

from core.workfile.setup.new_workfile import create_new_workfile
from core.ui.common.pickers import pick_save_file
from core.workfile.state.session_state import clear_workfile_session_state


def render_new_workfile_form():
    st.caption("All fields required.")

    description = st.text_input(
        "What is the new workfile for?",
        key="np_description",
        help="Short description — shown next to the ChartGen title for as long as this workfile is open.",
    )

    st.caption(
        "Suggested file naming: `CG_Emergency_Care_2026`, `CG_SE_Region_Briefing`"
    )
    if st.button("📁  Choose where to save…", key="np_browse", use_container_width=True):
        picked = pick_save_file(title="Save new workfile as", initial_file="CG_")
        if picked:
            st.session_state["np_save_path_val"] = picked
        st.rerun()

    save_path = st.session_state.get("np_save_path_val", "")
    if save_path:
        st.success(f"✔  {save_path}")
    else:
        st.caption("No location selected.")

    st.divider()

    if st.button("Create workfile", type="primary", key="np_create"):
        errors = []
        if not description.strip():
            errors.append("Please describe what this workfile is for.")
        if not save_path:
            errors.append("Please choose where to save the workfile.")
        if errors:
            for e in errors:
                st.error(e)
            return

        workfile_name = os.path.splitext(os.path.basename(save_path))[0]

        try:
            ws_new = create_new_workfile(
                workfile_path=save_path,
                workfile_name=workfile_name,
                description=description.strip(),
                username=st.session_state.get("username", ""),
            )
        except Exception as e:
            st.error(f"Could not create workfile: {e}")
            return

        st.session_state["workfile_state"] = ws_new
        st.session_state.pop("show_new_form", None)
        st.session_state.pop("np_save_path_val", None)
        clear_workfile_session_state()
        st.rerun()
