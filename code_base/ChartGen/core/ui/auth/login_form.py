"""
login_form.py
Page-level sign-in gate — rendered before anything else in app.py (sidebar,
workfile dialogs, tabs). Nothing past it renders until a valid token exists
for this session; there is no inline re-validation elsewhere (sign-in
status is shown read-only in the sidebar's "Version / Sign Out" expander —
there is no Config tab any more). Credential validation and token/username
handling live in core.session_shell.auth.login.
"""

import streamlit as st

from core.session_shell.auth.login import load_last_username, authenticate


def render_login_gate() -> bool:
    """
    Render the sign-in form and return False (caller should st.stop()) until
    st.session_state["token"] is set. The last successfully validated
    username is pre-filled from credentials.csv; the password is never
    stored and is re-entered every session.
    """
    if st.session_state.get("token"):
        return True

    st.title("ChartGen")
    st.caption("Analysis and Reporting software")
    st.subheader("Sign in")
    st.caption("Sign in with your NHS Benchmarking Network Toolkit credentials to continue.")

    default_email = load_last_username()

    with st.form("login_gate_form"):
        email = st.text_input("Email", value=default_email)
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            with st.spinner("Validating…"):
                try:
                    token = authenticate(email, password)
                    st.session_state["username"] = email.strip()
                    st.session_state["token"] = token
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign-in failed — please check your credentials. ({e})")

    return False
