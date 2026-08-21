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
    # Charts sheet sandbox state ("cs_" prefix, charts_tab.py) — cleared
    # wholesale on every Open/Close so a freshly opened workfile always
    # restores from its own saved charts_sheet_state (or starts blank),
    # never carrying over another workfile's in-progress sandbox values.
    for k in [k for k in st.session_state if k.startswith("cs_")]:
        del st.session_state[k]
    # Output Tables tab state ("ot_" prefix, output_tables_tab.py) — cleared
    # wholesale on every Open/Close for the same reason: a freshly opened
    # workfile should never inherit another workfile's selected table,
    # in-progress grid edits, or preview settings.
    for k in [k for k in st.session_state if k.startswith("ot_")]:
        del st.session_state[k]
    # Preview configuration state ("ots_" prefix, output_tables_tab.py) --
    # table type, tweaks, sizing, save-back target, paste-back. Kept
    # distinct from "ot_" (table selection, shared by Edit Grid and
    # Preview) so Reset never disturbs which table is selected. Cleared
    # wholesale on every Open/Close for the same reason as "cs_"/"ot_" above.
    for k in [k for k in st.session_state if k.startswith("ots_")]:
        del st.session_state[k]
