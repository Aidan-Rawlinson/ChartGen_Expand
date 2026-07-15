"""
sidebar.py
Sidebar file operations: New/Open/Save/Save As/Save and Close/Close Without
Saving/Sign out. Sets session-state flags for the modal forms in
workfile_dialogs.py to pick up; does not render those forms itself.
"""

import os

import streamlit as st

from core.ui.common.formatting import format_uk_time
from core.workfile.state.session_state import ws, clear_workfile_session_state
from core.workfile.state.workfile_file import save_workfile, close_workfile


def render_sidebar():
    with st.sidebar:
        st.markdown("## ChartGen")
        st.caption("Analysis and Reporting software")
        st.divider()

        w = ws()
        has_workfile = w is not None
        read_only = has_workfile and w.read_only

        if has_workfile:
            workfile_label = w.workfile_name or os.path.basename(w.workfile_path)
            dirty_marker = " ●" if w.dirty else ""
            st.markdown(f"**{workfile_label}**{dirty_marker}")
            if read_only:
                st.markdown(
                    "<span style='color:#c62828;font-weight:700;'>READ-ONLY</span>",
                    unsafe_allow_html=True,
                )
            if w.last_saved_by:
                st.caption(f"Saved by {w.last_saved_by}")
                st.caption(format_uk_time(w.last_saved_at))
            st.divider()

        # New / Open — active only when no workfile is open
        if st.button("New workfile", use_container_width=True, disabled=has_workfile):
            st.session_state["show_new_form"] = True
            st.session_state.pop("show_open_form", None)
            st.rerun()

        if st.button("Open workfile", use_container_width=True, disabled=has_workfile):
            st.session_state["show_open_form"] = True
            st.session_state.pop("show_new_form", None)
            st.rerun()

        st.divider()

        # Save / Save and Close are unavailable in a read-only session; Save As
        # remains available so a read-only session can become a normal one.
        if st.button("Save", use_container_width=True, disabled=not has_workfile or read_only):
            save_workfile(w, st.session_state["username"])
            st.rerun()

        if st.button("Save as", use_container_width=True, disabled=not has_workfile):
            st.session_state["show_save_as_form"] = True
            st.rerun()

        if st.button("Save and close", use_container_width=True, disabled=not has_workfile or read_only):
            save_workfile(w, st.session_state["username"])
            close_workfile(w)
            st.session_state.pop("workfile_state", None)
            clear_workfile_session_state()
            st.rerun()

        if st.button("Close without saving", use_container_width=True, disabled=not has_workfile):
            if has_workfile and w.dirty and not read_only:
                st.session_state["confirm_close_without_saving"] = True
            else:
                close_workfile(w)
                st.session_state.pop("workfile_state", None)
                clear_workfile_session_state()
            st.rerun()

        st.divider()
        st.caption(f"Signed in as {st.session_state.get('username', '')}")

        # Check for Update — available only with no workfile open (Decisions.md),
        # sidesteps mid-session file-lock issues entirely rather than handling them.
        if st.button("Check for update", use_container_width=True, disabled=has_workfile):
            st.session_state["show_update_form"] = True
            st.session_state.pop("update_check_result", None)
            st.rerun()

        if st.button("Sign out", use_container_width=True):
            if w:
                close_workfile(w)
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
