"""
session_state.py
Streamlit-side accessors for the current WorkfileState. WorkfileState itself
is owned by the workfile.state.workfile_file module (Architecture Decision 1);
these functions exist only because Streamlit's rerun model requires the
reference to be pulled back out of st.session_state on every script run —
swap out Streamlit and this module has no reason to exist. cached_files/
manifest/load_shape_ps are thin pass-throughs to
output_generation.execution.charts.cache_reader, supplying the current
WorkfileState automatically instead of it being typed at every call site.
"""

import streamlit as st

from core.output_generation.execution.charts.cache_reader import list_cached_files, load_shape, load_manifest
from core.workfile.state.workfile_file import WorkfileState


def ws() -> WorkfileState:
    """Return the current WorkfileState from session state."""
    return st.session_state.get("workfile_state")


def has_workfile() -> bool:
    return ws() is not None


def settings() -> dict:
    return ws().settings


def save_settings(s: dict):
    w = ws()
    w.settings = s
    w.dirty = True


def units() -> list:
    return ws().units


def manifest() -> dict:
    return load_manifest(ws())


def cached_files() -> list:
    return list_cached_files(ws())


def load_shape_ps(filename):
    return load_shape(filename, ws())


def clear_workfile_session_state():
    for k in ["ro_selected_idx", "ro_show_uploader", "run_log_rows",
              "pop_expander_open", "pop_expand_services_val", "pop_include_org_val"]:
        st.session_state.pop(k, None)
