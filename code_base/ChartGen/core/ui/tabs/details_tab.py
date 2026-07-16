"""
details_tab.py
Details tab — read-only view of file identity and save history. Project
identity (year, project_id, project_name) is deliberately not shown here —
none of it is a workfile-level concept any more; see Populations tab for
what a workfile actually contains (its tables).
"""

import streamlit as st

from core.ui.common.formatting import format_uk_time
from core.workfile.state.session_state import ws


def render_details_tab():
    st.header("Project Details")
    st.markdown(f"**File** &nbsp;&nbsp; `{ws().workfile_path}`")
    if ws().last_saved_by:
        st.markdown(f"**Last saved by** &nbsp;&nbsp; {ws().last_saved_by}")
        st.markdown(f"**Last saved at** &nbsp;&nbsp; {format_uk_time(ws().last_saved_at)}")
