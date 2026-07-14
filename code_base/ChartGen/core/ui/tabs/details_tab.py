"""
details_tab.py
Details tab — read-only view of project identity, time period, and file paths.
"""

import streamlit as st

from core.ui.common.formatting import format_uk_time
from core.workfile.state.session_state import ws, settings


def render_details_tab():
    st.header("Project Details")
    st.caption("These settings were configured at workfile creation.")
    s = settings()
    st.markdown(f"**Year** &nbsp;&nbsp; {s.get('year', '—')}")
    st.markdown(f"**Project** &nbsp;&nbsp; {s.get('project_name', '—')}")
    st.markdown(f"**Project ID** &nbsp;&nbsp; `{s.get('project_id', '—')}`")
    st.markdown(f"**File** &nbsp;&nbsp; `{ws().workfile_path}`")
    if ws().last_saved_by:
        st.markdown(f"**Last saved by** &nbsp;&nbsp; {ws().last_saved_by}")
        st.markdown(f"**Last saved at** &nbsp;&nbsp; {format_uk_time(ws().last_saved_at)}")
