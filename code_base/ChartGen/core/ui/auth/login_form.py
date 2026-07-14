"""
login_form.py
Sign-in form and the authentication gate — widgets only. Credential
validation and token handling live in core.session_shell.auth.login.
"""

import streamlit as st

from core.session_shell.auth.login import load_last_username, authenticate


def _render_login():
    st.set_page_config(page_title="ChartGen — Sign In", layout="centered")
    st.title("ChartGen")
    st.caption("Analysis and Reporting software")
    st.subheader("Sign in")

    default_email = load_last_username()

    with st.form("login_form"):
        email = st.text_input("Email", value=default_email)
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            with st.spinner("Signing in…"):
                try:
                    token = authenticate(email, password)
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = email.strip()
                    st.session_state["token"] = token
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign in failed — please check your credentials. ({e})")


def require_authentication():
    """
    Show the login form and halt the script (st.stop) if not yet authenticated.
    No-op if already signed in this session.
    """
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        _render_login()
        st.stop()
