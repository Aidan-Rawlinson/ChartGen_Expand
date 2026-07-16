"""
open_workfile_form.py
UI for Open Workfile: file picker, then the advisory-lock decision step
(Open / Open Read-Only / Cancel). Lock-state classification and the actual
Open/Open Read-Only mechanics live in core.session_shell.lifecycle.concurrency
— this module only renders the decision step and picks which message to show
for the classified state.
"""

import os

import streamlit as st

from core.ui.common.formatting import format_uk_time
from core.ui.common.pickers import pick_workfile_file
from core.workfile.state.session_state import clear_workfile_session_state
from core.workfile.state.workfile_file import read_workfile_info
from core.shared.infrastructure.version_compatibility import (
    is_file_version_compatible, get_software_id,
)
from core.session_shell.lifecycle.concurrency import (
    classify_lock_state, open_normal, open_read_only,
)


def _clear_open_flow_state():
    """Clear all session state used by the Open Workfile flow, including any pending decision."""
    for k in ["show_open_form", "op_workfile_path_val", "op_pending_path", "op_pending_info"]:
        st.session_state.pop(k, None)


def _render_open_decision():
    """Show the clean/locked decision step for a validated .cgw path, offering Open or Open Read-Only."""
    path = st.session_state.get("op_pending_path")
    if not path:
        return

    info = st.session_state.get("op_pending_info") or {}
    current_user = st.session_state.get("username", "")
    lock_state = classify_lock_state(info, current_user)
    locked_by = (info.get("locked_by") or "").strip()
    locked_at = info.get("locked_at", "")

    if lock_state == "unlocked":
        st.info("This workfile is not currently marked as open by anyone.")
    elif lock_state == "locked_by_self":
        st.warning(
            "This workfile was not closed down properly last time it was used, "
            "or it may still be open elsewhere under your account. Proceeding "
            "may overwrite work if it is still open elsewhere. Choose Open "
            "Read-Only if you are unsure."
        )
        st.caption(f"Last marked open: {format_uk_time(locked_at)}")
    else:
        st.warning(
            f"This workfile is currently marked as open by **{locked_by}** as of "
            f"{format_uk_time(locked_at)}. Opening it while they may still be "
            "working in it could result in one of you losing changes. Choose "
            "Open Read-Only to view without risk, or Open to take on that risk "
            "yourself."
        )

    c1, c2, c3 = st.columns([1, 1, 1])

    if c1.button("Open", type="primary", key="op_decision_open"):
        st.session_state["workfile_state"] = open_normal(path, current_user)
        _clear_open_flow_state()
        clear_workfile_session_state()
        st.rerun()

    if c2.button("Open Read-Only", key="op_decision_readonly"):
        st.session_state["workfile_state"] = open_read_only(path)
        _clear_open_flow_state()
        clear_workfile_session_state()
        st.rerun()

    if c3.button("Cancel", key="op_decision_cancel"):
        _clear_open_flow_state()
        st.rerun()


def render_open_workfile_form():
    col_browse2, col_clear2 = st.columns([2, 1])
    with col_browse2:
        if st.button("📂  Browse for .cgw file…", key="op_browse", use_container_width=True):
            picked = pick_workfile_file()
            if picked:
                st.session_state["op_workfile_path_val"] = picked
            st.rerun()
    with col_clear2:
        if st.button("Clear", key="op_clear", disabled=not st.session_state.get("op_workfile_path_val")):
            st.session_state["op_workfile_path_val"] = ""
            st.rerun()

    workfile_path_val = st.session_state.get("op_workfile_path_val", "")
    if workfile_path_val:
        st.success(f"✔  {workfile_path_val}")
    else:
        st.caption("No file selected.")

    st.divider()

    if not st.session_state.get("op_pending_path"):
        if st.button("Open", type="primary", key="op_open"):
            path = st.session_state.get("op_workfile_path_val", "").strip()
            if not path:
                st.error("Please enter a path.")
                return
            if not os.path.exists(path):
                st.error("File not found.")
                return
            if not path.endswith(".cgw"):
                st.error("Please select a .cgw file.")
                return
            info = read_workfile_info(path)
            file_version_id = info.get("file_version_id", "")
            if not is_file_version_compatible(file_version_id):
                st.error(
                    f"This workfile can't be opened by this version of ChartGen "
                    f"({get_software_id()}). Its internal file version "
                    f"(\"{file_version_id or 'unknown'}\") isn't supported by this build. "
                    "Check you're running the version of ChartGen this workfile was "
                    "last saved with."
                )
                return
            st.session_state["op_pending_path"] = path
            st.session_state["op_pending_info"] = info
            st.rerun()

    _render_open_decision()
