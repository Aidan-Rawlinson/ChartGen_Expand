"""
app.py
ChartGen Python Prototype — Streamlit entry point.

This module only sequences the page: apply any startup workfile, render
the sidebar, render whichever modal dialog is active, then render the
tabs. All UI construction, form logic, and business logic live in their
owning modules under core/. No authentication gate exists here —
credentials are validated inline within the Config tab, not at launch.
"""

import os
import sys
import html

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from core.ui.workfile.sidebar import render_sidebar
from core.ui.workfile.workfile_dialogs import render_workfile_dialogs
from core.workfile.state.session_state import ws, has_workfile
from core.session_shell.lifecycle.startup_file import apply_startup_workfile
from core.ui.tabs import (
    details_tab, config_tab, imports_tab, populations_tab, select_tab,
    text_tab, running_order_tab, charts_tab, outputs_tab,
)


apply_startup_workfile()

st.set_page_config(page_title="ChartGen", layout="wide")

if st.session_state.get("startup_file_error"):
    st.error(st.session_state.pop("startup_file_error"))

render_sidebar()
render_workfile_dialogs()

if not has_workfile():
    st.title("ChartGen")
    st.caption("Analysis and Reporting software")
    st.info("No workfile open. Use the sidebar to create a new workfile or open an existing one.")
    st.stop()

ws_main = ws()

# Header: "ChartGen" title, plus whichever badges currently apply — the
# workfile's own description (what it's for, set at New Workfile time; for
# the person, not the system) and a READ-ONLY marker. description is free
# text typed by a user, so it's HTML-escaped before going into unsafe_allow_html.
badges = []
description = (ws_main.settings.get("description", "") if ws_main else "").strip()
if description:
    badges.append(
        f'<span style="color:#FF4B4B;font-weight:600;font-size:1.1em;">{html.escape(description)}</span>'
    )
if ws_main and ws_main.read_only:
    badges.append(
        '<span style="color:#c62828;font-weight:800;font-size:1.1em;'
        'letter-spacing:0.05em;">READ-ONLY</span>'
    )

if badges:
    st.markdown(
        '<div style="display:flex;align-items:baseline;gap:14px;">'
        '<h1 style="margin:0;padding:0;">ChartGen</h1>' + "".join(badges) +
        '</div>',
        unsafe_allow_html=True,
    )
else:
    st.title("ChartGen")
st.caption("Analysis and Reporting software")

(tab_details, tab_config, tab_imports, tab_populations, tab_select,
 tab_text, tab_running_order, tab_charts, tab_outputs) = st.tabs([
    "Details", "Config", "Imports", "Populations", "Select",
    "Text", "Running Order", "Charts", "Outputs"
])

with tab_details:
    details_tab.render_details_tab()

with tab_config:
    config_tab.render_config_tab()

with tab_populations:
    populations_tab.render_populations_tab()

with tab_select:
    select_tab.render_select_tab()

with tab_imports:
    imports_tab.render_imports_tab()

with tab_text:
    text_tab.render_text_tab()

with tab_running_order:
    running_order_tab.render_running_order_tab()

with tab_charts:
    charts_tab.render_charts_tab()

with tab_outputs:
    outputs_tab.render_outputs_tab()
