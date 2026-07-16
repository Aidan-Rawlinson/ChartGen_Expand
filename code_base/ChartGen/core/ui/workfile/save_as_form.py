"""
save_as_form.py
UI for Save Workfile As: a single native Save dialog for name and location
(the OS dialog itself confirms overwrite, so this module no longer needs
its own overwrite-confirmation step), then hands off to
core.workfile.setup.save_as for the template copy, lock transfer, and save.
This module owns no business logic itself.
"""

import os

import streamlit as st

from core.ui.common.pickers import pick_save_file
from core.workfile.setup.save_as import save_as, is_same_as_original_folder
from core.workfile.state.session_state import ws


def render_save_as_form():
    ws_cur = ws()

    st.caption("Choose a new name and/or location. The cleaned PowerPoint template is copied alongside it.")
    if ws_cur.read_only:
        st.info(
            "This is a read-only session. Saving into a different folder creates "
            "a new, independent workfile that you can then edit normally."
        )

    if st.button("📁  Choose where to save…", key="sa_browse", use_container_width=True):
        picked = pick_save_file(
            title="Save workfile as",
            initial_file=ws_cur.workfile_name or "",
        )
        if picked:
            st.session_state["sa_save_path_val"] = picked
        st.rerun()

    save_path = st.session_state.get("sa_save_path_val", "")
    if save_path:
        st.success(f"✔  {save_path}")
    else:
        st.caption("No location selected.")

    st.divider()
    col_save, col_cancel = st.columns([1, 1])

    if col_save.button("Save as", type="primary", key="sa_save"):
        errors = []
        if not save_path:
            errors.append("Please choose where to save the workfile.")
        elif ws_cur.read_only and is_same_as_original_folder(ws_cur, os.path.dirname(save_path)):
            errors.append(
                "This is a read-only session — choose a different folder "
                "from the original workfile's location."
            )
        if errors:
            for e in errors:
                st.error(e)
        else:
            new_name = os.path.splitext(os.path.basename(save_path))[0]
            save_as(ws_cur, save_path, new_name, st.session_state["username"])
            st.session_state.pop("show_save_as_form", None)
            st.session_state.pop("sa_save_path_val", None)
            st.rerun()

    if col_cancel.button("Cancel", key="sa_cancel"):
        st.session_state.pop("show_save_as_form", None)
        st.session_state.pop("sa_save_path_val", None)
        st.rerun()
