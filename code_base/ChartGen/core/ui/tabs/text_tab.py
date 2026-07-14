"""
text_tab.py
Text tab — lists available text tags with a live preview of each tag's value
for the currently selected reporting unit.
"""

import streamlit as st

from core.shared.infrastructure.report_context import build_report_context
from core.workfile.state.session_state import settings, units


def render_text_tab():
    st.header("Text — Text Tags")
    st.caption(
        "Add `update_text` rows to the Running Order to replace these text tags "
        "in your PowerPoint template at generation time."
    )
    rc_text = build_report_context(settings(), units())
    preview_value = rc_text.unit_name if rc_text else "— no reporting unit selected —"

    st.dataframe(
        {
            "Text Tag": ["[selected-reporting-unit-name]"],
            "Replaced with": ["Unit name"],
            "Current value": [preview_value],
        },
        use_container_width=True, hide_index=True,
    )
