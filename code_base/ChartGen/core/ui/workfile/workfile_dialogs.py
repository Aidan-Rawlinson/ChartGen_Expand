"""
workfile_dialogs.py
Full-page modal dialogs triggered by sidebar actions: the close-without-saving
confirmation, and the New/Open/Save As forms. Each halts the rest of the page
(st.stop()) while active, same as the sidebar buttons that trigger them.
"""

import streamlit as st

from core.ui.workfile.new_workfile_form import render_new_workfile_form
from core.ui.workfile.open_workfile_form import render_open_workfile_form
from core.ui.workfile.save_as_form import render_save_as_form
from core.ui.workfile.update_form import render_update_form
from core.workfile.state.session_state import ws, clear_workfile_session_state
from core.workfile.state.workfile_file import close_workfile


def render_workfile_dialogs():
    """Render whichever modal dialog is currently flagged in session state, then stop the script."""
    if st.session_state.get("confirm_close_without_saving"):
        st.warning("Close without saving? Unsaved changes will be lost.")
        c1, c2 = st.columns(2)
        if c1.button("Close without saving", type="primary"):
            close_workfile(ws())
            st.session_state.pop("workfile_state", None)
            clear_workfile_session_state()
            st.session_state.pop("confirm_close_without_saving", None)
            st.rerun()
        if c2.button("Cancel"):
            st.session_state.pop("confirm_close_without_saving", None)
            st.rerun()
        st.stop()

    if st.session_state.get("show_new_form"):
        st.title("New Workfile")
        render_new_workfile_form()
        st.stop()

    if st.session_state.get("show_open_form"):
        st.title("Open Workfile")
        render_open_workfile_form()
        st.stop()

    if st.session_state.get("show_save_as_form"):
        st.title("Save Workfile As")
        render_save_as_form()
        st.stop()

    if st.session_state.get("show_update_form"):
        st.title("Check for Update")
        render_update_form()
        st.stop()
