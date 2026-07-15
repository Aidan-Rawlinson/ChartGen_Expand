"""
startup_file.py
Optional double-click-to-open support: if ChartGen was launched with a .cgw
path as a startup argument (e.g. via the .cgw file association), route it
into the existing Open Workfile flow - same compatibility check, same
lock-state decision step (Functional Spec Section 5) - rather than opening
it silently.

Opening via double-click is optional, the same way opening Word or Excel
without a file is normal: with no startup argument, ChartGen starts exactly
as it does today, with no workfile loaded.
"""

import os
import sys

import streamlit as st

from core.shared.infrastructure.version_compatibility import is_file_version_compatible
from core.workfile.state.workfile_file import read_workfile_info


def get_startup_workfile_path() -> str:
    """
    Return a .cgw path passed as a startup argument, if any.
    Streamlit passes script arguments after a literal '--' separator
    (e.g. `streamlit run app.py -- "C:\\path\\to\\File.cgw"`), so sys.argv[1:]
    holds only the app's own arguments, never Streamlit's own flags.
    """
    args = sys.argv[1:]
    if not args:
        return ""
    path = args[0].strip('"')
    if path.endswith(".cgw") and os.path.exists(path):
        return path
    return ""


def apply_startup_workfile():
    """
    On first run of the session only (Streamlit reruns the whole script on
    every interaction, so this must not re-trigger), if a startup .cgw path
    was given, route it into the Open Workfile flow's existing validation
    and lock-decision step. Never opens silently, never bypasses the file
    version compatibility hard refuse.
    """
    if st.session_state.get("startup_file_checked"):
        return
    st.session_state["startup_file_checked"] = True

    path = get_startup_workfile_path()
    if not path:
        return

    info = read_workfile_info(path)
    file_version_id = info.get("file_version_id", "")
    if not is_file_version_compatible(file_version_id):
        st.session_state["startup_file_error"] = (
            f"The workfile ChartGen was opened with (\"{os.path.basename(path)}\") "
            "can't be opened by this version of ChartGen - its internal file "
            "version isn't supported by this build."
        )
        return

    # Pre-populate the existing Open Workfile flow's state as if the user
    # had picked this file and pressed Open - reuses the same lock-state
    # decision step, rather than a separate silent-open path for this route.
    st.session_state["show_open_form"] = True
    st.session_state["op_workfile_path_val"] = path
    st.session_state["op_pending_path"] = path
    st.session_state["op_pending_info"] = info
