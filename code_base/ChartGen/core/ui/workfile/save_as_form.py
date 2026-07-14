"""
save_as_form.py
UI for Save Workfile As: collects the new name and save location, shows the
overwrite-confirmation step, and hands off to core.workfile.setup.save_as
for the template copy, lock transfer, and save. This module owns no
business logic itself.
"""

import os

import streamlit as st

from core.ui.common.pickers import pick_folder
from core.workfile.setup.save_as import save_as, is_same_as_original_folder
from core.workfile.state.session_state import ws


def render_save_as_form():
    ws_cur = ws()

    st.caption("Choose a new location and/or name. The cleaned PowerPoint template is copied alongside it.")
    if ws_cur.read_only:
        st.info(
            "This is a read-only session. Saving into a different folder creates "
            "a new, independent workfile that you can then edit normally."
        )

    workfile_name = st.text_input(
        "Workfile name",
        value=ws_cur.workfile_name or "",
        key="sa_workfile_name",
        help="Used as the file name (without .cgw).",
    )

    col_browse, col_clear = st.columns([2, 1])
    with col_browse:
        if st.button("📂  Browse for save location…", key="sa_browse", use_container_width=True):
            picked = pick_folder()
            if picked:
                st.session_state["sa_save_folder_val"] = picked
            st.rerun()
    with col_clear:
        if st.button("Clear", key="sa_clear", disabled=not st.session_state.get("sa_save_folder_val")):
            st.session_state["sa_save_folder_val"] = ""
            st.rerun()

    folder_val = st.session_state.get("sa_save_folder_val", "")
    if folder_val:
        st.success(f"✔  {folder_val}")
    else:
        st.caption("No location selected.")

    st.divider()
    col_save, col_cancel = st.columns([1, 1])

    def _finish(new_workfile_path: str, new_name: str):
        save_as(ws_cur, new_workfile_path, new_name, st.session_state["username"])
        st.session_state.pop("show_save_as_form", None)
        st.session_state.pop("sa_save_folder_val", None)
        st.session_state.pop("sa_confirm_overwrite_path", None)
        st.rerun()

    if col_save.button("Save as", type="primary", key="sa_save"):
        errors = []
        name = workfile_name.strip()
        if not name:
            errors.append("Please enter a workfile name.")
        folder = folder_val.strip()
        if not folder:
            errors.append("Please choose a save location.")
        elif not os.path.isdir(folder):
            errors.append(f"Save location not found: {folder}")
        elif ws_cur.read_only and is_same_as_original_folder(ws_cur, folder):
            errors.append(
                "This is a read-only session — choose a different folder "
                "from the original workfile's location."
            )
        if errors:
            for e in errors:
                st.error(e)
        else:
            new_workfile_path = os.path.join(folder, f"{name}.cgw")
            if os.path.exists(new_workfile_path):
                st.session_state["sa_confirm_overwrite_path"] = new_workfile_path
                st.session_state["sa_confirm_overwrite_name"] = name
                st.rerun()
            else:
                _finish(new_workfile_path, name)

    if col_cancel.button("Cancel", key="sa_cancel"):
        st.session_state.pop("show_save_as_form", None)
        st.session_state.pop("sa_save_folder_val", None)
        st.rerun()

    overwrite_path = st.session_state.get("sa_confirm_overwrite_path")
    if overwrite_path:
        st.warning(f"A file already exists at {overwrite_path}. Overwrite it?")
        c1, c2 = st.columns(2)
        if c1.button("Overwrite", type="primary", key="sa_overwrite_confirm"):
            _finish(overwrite_path, st.session_state.get("sa_confirm_overwrite_name", workfile_name.strip()))
        if c2.button("Cancel", key="sa_overwrite_cancel"):
            st.session_state.pop("sa_confirm_overwrite_path", None)
            st.session_state.pop("sa_confirm_overwrite_name", None)
            st.rerun()
