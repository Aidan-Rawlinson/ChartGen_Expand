"""
login_form.py
Credentials box widget — rendered inline within the Config tab, not as a
page-level gate. Credential validation and token handling live in
core.session_shell.auth.login. No workfile-launch gate exists any more;
see config_tab.py for where this is called from.
"""

import streamlit as st

from core.session_shell.auth.login import load_last_username, authenticate


def render_credentials_box():
    """
    Render the single credentials box (username, password, validate button).
    On success: stores the session token and username in session state and
    shows a confirmation message. On failure: shows an error, no token
    stored. Safe to call every rerun — it does not gate or halt the script.
    """
    st.subheader("NHS Annual and Indicator Toolkits")

    current_username = st.session_state.get("username", "")
    if current_username:
        st.caption(f"Signed in this session as {current_username}")
    else:
        st.caption("Not signed in this session.")

    default_email = current_username or load_last_username()

    with st.form("credentials_form"):
        email = st.text_input("Email", value=default_email)
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Validate credentials")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            with st.spinner("Validating…"):
                try:
                    token = authenticate(email, password)
                    st.session_state["username"] = email.strip()
                    st.session_state["token"] = token
                    st.success("Credentials validated.")
                except Exception as e:
                    st.error(f"Validation failed — please check your credentials. ({e})")
