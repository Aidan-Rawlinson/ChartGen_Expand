"""
session_state.py
Streamlit-side accessors for the current WorkfileState, which is owned by
workfile.state.workfile_file. These exist only because Streamlit's rerun
model requires the reference to be pulled back out of st.session_state on
every script run.

cached_files, manifest and load_shape_ps are pass-throughs to
charts.cache_reader, supplying the current WorkfileState automatically.
"""

import streamlit as st

from chartgen.output_generation.execution.charts.cache_reader import list_cached_files, load_shape, load_manifest
from chartgen.workfile.state.workfile_file import WorkfileState, master_table_rows


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


def master_table() -> list:
    """Rows of the master table — whichever table sits first in table_order."""
    return master_table_rows(ws())


def manifest() -> dict:
    return load_manifest(ws())


def cached_files() -> list:
    return list_cached_files(ws())


def load_shape_ps(filename):
    return load_shape(filename, ws())


def clear_workfile_session_state():
    for k in ["ro_selected_idx", "ro_show_uploader", "run_log_rows",
              "pop_expander_open", "sb_description_input"]:
        st.session_state.pop(k, None)
    # Every per-tab prefix is cleared wholesale on Open and Close, so a
    # freshly opened workfile restores from its own saved state, or starts
    # blank, and never inherits another workfile's in-progress values.
    #   cs_   Charts sheet sandbox
    #   ot_   Output Tables selection, shared by Edit Grid and Preview
    #   ots_  Output Tables preview configuration, kept separate from ot_ so
    #         Reset never disturbs which table is selected
    for k in [k for k in st.session_state if k.startswith("cs_")]:
        del st.session_state[k]
    for k in [k for k in st.session_state if k.startswith("ot_")]:
        del st.session_state[k]
    for k in [k for k in st.session_state if k.startswith("ots_")]:
        del st.session_state[k]
