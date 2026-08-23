"""
compact_layout.py
Drop-in replacements for st.subheader, st.caption and st.divider carrying
tighter margins than Streamlit's own block spacing.

Per-element markdown substitutions, used at individual call sites. Distinct
from layout_css.py, which is a global override: Streamlit gives no reliable
per-tab selector to scope a global rule to some tabs and not others.

st.markdown still parses ordinary markdown inside the surrounding HTML tags
here, so caption text using backticks or bold needs no rewriting.
"""

import streamlit as st


def tight_divider():
    """Compact replacement for st.divider() — a few px of margin instead of Streamlit's ~1rem."""
    st.markdown('<hr style="border:none;border-top:1px solid #ddd;margin:4px 0;">', unsafe_allow_html=True)


def tight_subheader(text: str):
    """Compact replacement for st.subheader(text) — a section label, not a full heading."""
    st.markdown(f'<p style="font-weight:600;font-size:1.0rem;margin:8px 0 2px 0;">{text}</p>',
                unsafe_allow_html=True)


def tight_caption(text: str):
    """Compact replacement for st.caption(text) — same muted styling, tighter margin."""
    st.markdown(f'<p style="font-size:0.85em;color:#666;margin:0 0 4px 0;">{text}</p>',
                unsafe_allow_html=True)
