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


def _group_spacer():
    """
    Extra breathing room between button groups in the sidebar, in place of
    st.divider(). No line — every attempt at combining a visible line with
    reliable, even spacing ran into some form of Streamlit layout quirk
    (trailing space collapsing regardless of technique, or a fixed-height
    box overlapping the next element); the plain spacer alone reliably gave
    correct, even spacing, so that's what's kept.
    """
    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("## ChartGen")
        st.caption("Analysis and Reporting software")
        _group_spacer()

        w = ws()
        has_workfile = w is not None
        read_only = has_workfile and w.read_only

        if has_workfile:
            if read_only:
                st.markdown(
                    "<span style='color:#c62828;font-weight:700;'>READ-ONLY</span>",
                    unsafe_allow_html=True,
                )
            with st.expander("Workfile Details", expanded=False):
                description = (w.settings.get("description", "") if w.settings else "").strip()
                workfile_label = w.workfile_name or os.path.basename(w.workfile_path)

                st.caption("File name")
                st.write(workfile_label)

                st.caption("Description")
                st.write(description or "—")

                st.caption("Full file path")
                st.write(w.workfile_path)

                st.caption("Last saved by")
                st.write(w.last_saved_by or "—")

                st.caption("Last saved at")
                st.write(format_uk_time(w.last_saved_at) if w.last_saved_at else "—")

        # New / Open — active only when no workfile is open
        if st.button("New workfile", use_container_width=True, disabled=has_workfile):
            st.session_state["show_new_form"] = True
            st.session_state.pop("show_open_form", None)
            st.rerun()

        if st.button("Open workfile", use_container_width=True, disabled=has_workfile):
            st.session_state["show_open_form"] = True
            st.session_state.pop("show_new_form", None)
            st.rerun()

        _group_spacer()

        # Save / Save and Close are unavailable in a read-only session; Save As
        # remains available so a read-only session can become a normal one.
        if st.button("Save", use_container_width=True, disabled=not has_workfile or read_only):
            save_workfile(w, st.session_state.get("username", ""))
            st.rerun()

        if st.button("Save as", use_container_width=True, disabled=not has_workfile):
            st.session_state["show_save_as_form"] = True
            st.rerun()

        if st.button("Save and close", use_container_width=True, disabled=not has_workfile or read_only):
            save_workfile(w, st.session_state.get("username", ""))
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

        _group_spacer()

        with st.expander("Version / Sign Out", expanded=False):
            _username = st.session_state.get("username", "")
            st.caption(f"Signed in as {_username}" if _username else "Not signed in")

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
