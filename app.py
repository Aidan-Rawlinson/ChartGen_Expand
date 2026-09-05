"""
app.py
ChartGen Python Prototype — Streamlit entry point.

This module only sequences the page: gate on sign-in, apply any startup
workfile, render the sidebar, render whichever modal dialog is active,
then render the tabs. All UI construction, form logic, and business logic
live in their owning modules under chartgen/. The sign-in gate
(chartgen.ui.auth.login_form.render_login_gate) is the first thing rendered —
nothing else in the app (sidebar, workfile open/new, tabs) is reachable
without a validated session token, whether ChartGen was launched directly
or via a .cgw file association.
"""

import os
import sys
import html

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from chartgen.ui.auth.login_form import render_login_gate
from chartgen.ui.common.flash import render_flashes
from chartgen.ui.common.layout_css import inject_layout_css
from chartgen.ui.workfile.sidebar import render_sidebar
from chartgen.ui.workfile.workfile_dialogs import render_workfile_dialogs
from chartgen.workfile.state.session_state import ws, has_workfile
from chartgen.session_shell.lifecycle.font_startup import apply_font_startup
from chartgen.session_shell.lifecycle.startup_file import apply_startup_workfile
from chartgen.ui.tabs import (
    imports_tab, populations_tab, select_tab,
    text_tab, running_order_tab, charts_tab, output_tables_tab, outputs_tab,
    settings_tab, notes_tab,
)


st.set_page_config(page_title="ChartGen", layout="wide")
inject_layout_css()

if not render_login_gate():
    st.stop()

apply_startup_workfile()

# Bundled fonts: registered with matplotlib so charts draw in them, and
# installed into Windows so PowerPoint can display them. Once per session,
# and it writes nothing when everything is already in place.
apply_font_startup()

if st.session_state.get("startup_file_error"):
    st.error(st.session_state.pop("startup_file_error"))

# A font that could not be installed still renders correctly in ChartGen's
# own charts, so this is a warning rather than an error — but PowerPoint will
# substitute, which is not something to discover in a finished report.
for font_problem in st.session_state.pop("font_install_problems", []):
    st.warning(font_problem)

# Confirmations queued by a surface that had to st.rerun() straight after
# acting — see ui/common/flash.py. Shown here, once per run, before
# anything that might stop the script short of the tabs.
render_flashes()

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

(tab_imports, tab_populations, tab_select,
 tab_text, tab_running_order, tab_charts, tab_output_tables, tab_outputs,
 tab_settings, tab_notes) = st.tabs([
    "Imports", "Populations", "Select",
    "Text", "Running Order", "Charts", "Tables", "Outputs", "Settings", "Notes"
])

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

with tab_output_tables:
    output_tables_tab.render_output_tables_tab()

with tab_outputs:
    outputs_tab.render_outputs_tab()

with tab_settings:
    settings_tab.render_settings_tab()

with tab_notes:
    notes_tab.render_notes_tab()
