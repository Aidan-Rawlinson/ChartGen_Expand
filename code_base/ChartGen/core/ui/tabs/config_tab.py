"""
config_tab.py
Config tab — credentials, plus (in future) management of reference CSVs and
other runtime configuration files. Only accessible with a workfile open,
same as every other tab.
"""

import streamlit as st

from core.ui.auth.login_form import render_credentials_box


def render_config_tab():
    st.header("User Controlled Configuration Files")

    render_credentials_box()

    st.divider()
    st.info("Further config file management coming soon.")
