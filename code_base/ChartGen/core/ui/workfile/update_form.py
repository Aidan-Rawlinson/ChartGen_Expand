"""
update_form.py
"Check for Update" modal, triggered from the sidebar (available only with
no workfile open - Decisions.md). Runs the version comparison, and on
confirmation, copies the release installer to a temp location, launches it,
then exits ChartGen's own process so the installer can overwrite the
install in place.
"""

import os
import shutil
import subprocess
import tempfile

import streamlit as st

from core.session_shell.lifecycle.update_check import check_for_update


def _launch_installer_and_exit(installer_path: str):
    """Copy the installer to a temp location, launch it, then exit ChartGen."""
    temp_dir = tempfile.mkdtemp(prefix="chartgen_update_")
    temp_installer = os.path.join(temp_dir, os.path.basename(installer_path))
    shutil.copy2(installer_path, temp_installer)

    subprocess.Popen([temp_installer], close_fds=True)

    # Exit this process immediately so the installer isn't blocked by files
    # this session is still holding open. A normal Streamlit shutdown isn't
    # designed to be triggered from within a callback, so this is a
    # deliberate hard exit, not a bug.
    os._exit(0)


def render_update_form():
    st.caption("Compares this installed version against the release copy on SharePoint.")

    if "update_check_result" not in st.session_state:
        st.session_state["update_check_result"] = check_for_update()

    result = st.session_state["update_check_result"]

    if result["status"] == "error":
        st.error(result["message"])

    elif result["status"] == "up_to_date":
        st.success(f"You're up to date (version {result['local_version']}).")

    elif result["status"] == "update_available":
        st.info(
            f"An update is available: **{result['release_version']}** "
            f"(you have **{result['local_version']}**)."
        )
        st.warning(
            "Installing will close ChartGen. Make sure any work is saved "
            "before continuing - this check is only available with no "
            "workfile open, but close any other open sessions too."
        )
        if st.button("Download and install now", type="primary", key="update_confirm"):
            _launch_installer_and_exit(result["installer_path"])

    c1, c2 = st.columns(2)
    if c1.button("Check again", key="update_recheck"):
        st.session_state["update_check_result"] = check_for_update()
        st.rerun()
    if c2.button("Close", key="update_close"):
        st.session_state.pop("show_update_form", None)
        st.session_state.pop("update_check_result", None)
        st.rerun()
