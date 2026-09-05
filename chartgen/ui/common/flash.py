"""
flash.py
A confirmation queued on one run and shown on the next.

Every save-back surface ends in st.rerun(), which is needed because the
widgets it has to update have already been instantiated this run. A rerun
discards whatever the current run has drawn, so an st.success() written
immediately before one is never seen: the message is created and thrown
away in the same breath. That is why saving appeared to confirm nothing.

Queue the message instead, and let the next run show it. st.toast is used
rather than st.success because a save's confirmation belongs to the moment,
not to a panel: it appears wherever the user is looking and clears itself,
so it does not accumulate down a rail of collapsed expanders.

The queue key carries no tab prefix on purpose. It is not sandbox state,
and a message queued just before an Open or Close should still be shown
rather than swept away with that tab's session keys.
"""

import streamlit as st

_FLASH_KEY = "pending_flash_messages"


def queue_flash(message: str, icon: str = "✅"):
    """Queue a confirmation for the next run. Safe to call immediately before st.rerun()."""
    st.session_state.setdefault(_FLASH_KEY, []).append((message, icon))


def render_flashes():
    """
    Show and clear every queued confirmation. Called once per run from
    app.py, before the tabs, so a message queued by any surface appears
    wherever the user has since navigated to.
    """
    for message, icon in st.session_state.pop(_FLASH_KEY, []):
        st.toast(message, icon=icon)
