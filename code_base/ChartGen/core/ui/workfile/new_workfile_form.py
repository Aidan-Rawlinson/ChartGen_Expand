"""
new_workfile_form.py
UI for the New Workfile flow: collects year, project, name, and save
location, then hands off to core.workfile.setup.new_workfile for the API
calls and units-table construction. This module owns no business logic itself.
"""

import datetime
import os

import streamlit as st

from core.workfile.setup.new_workfile import list_projects_for_year, create_new_workfile
from core.ui.common.pickers import pick_folder
from core.workfile.state.session_state import clear_workfile_session_state


def render_new_workfile_form():
    st.caption("All fields required.")

    current_year = datetime.date.today().year
    year_options = [current_year, current_year - 1]
    selected_year = st.selectbox("Year", options=year_options, index=0, key="np_year")

    @st.cache_data(show_spinner=False)
    def _cached_projects(year, token):
        return list_projects_for_year(year, token)

    with st.spinner(f"Loading projects for {selected_year}…"):
        try:
            project_options = _cached_projects(selected_year, st.session_state["token"])
        except Exception as e:
            st.error(f"Could not load project list: {e}")
            project_options = {}

    selected_project_name = st.selectbox(
        "Project", options=list(project_options.keys()), index=None,
        placeholder="Select a project…", key="np_project", disabled=not project_options,
    )
    selected_project_id = project_options.get(selected_project_name, "")

    workfile_name = st.text_input(
        "Workfile name",
        value=selected_project_name or "",
        key="np_workfile_name",
        help="Used as the file name (without .cgw).",
    )

    col_browse, col_clear = st.columns([2, 1])
    with col_browse:
        if st.button("📂  Browse for save location…", key="np_browse", use_container_width=True):
            picked = pick_folder()
            if picked:
                st.session_state["np_save_folder_val"] = picked
            st.rerun()
    with col_clear:
        if st.button("Clear", key="np_clear", disabled=not st.session_state.get("np_save_folder_val")):
            st.session_state["np_save_folder_val"] = ""
            st.rerun()

    folder_val = st.session_state.get("np_save_folder_val", "")
    if folder_val:
        st.success(f"✔  {folder_val}")
    else:
        st.caption("No location selected.")

    st.divider()

    if st.button("Create workfile", type="primary", key="np_create"):
        errors = []
        if not selected_project_id:
            errors.append("Please select a project.")
        if not workfile_name.strip():
            errors.append("Please enter a workfile name.")
        folder = st.session_state.get("np_save_folder_val", "").strip()
        if not folder:
            errors.append("Please enter a save location.")
        elif not os.path.isdir(folder):
            errors.append(f"Save location not found: {folder}")
        if errors:
            for e in errors:
                st.error(e)
            return

        workfile_path = os.path.join(folder, f"{workfile_name.strip()}.cgw")

        with st.spinner("Fetching project data…"):
            try:
                ws_new = create_new_workfile(
                    workfile_path=workfile_path,
                    workfile_name=workfile_name.strip(),
                    year=selected_year,
                    project_id=selected_project_id,
                    project_name=selected_project_name,
                    token=st.session_state["token"],
                    username=st.session_state["username"],
                )
            except Exception as e:
                st.error(f"Could not create workfile: {e}")
                return

        st.session_state["workfile_state"] = ws_new
        st.session_state.pop("show_new_form", None)
        st.session_state.pop("np_save_folder", None)
        clear_workfile_session_state()
        st.rerun()
