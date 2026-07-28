"""
compact_layout.py
Small drop-in replacements for st.subheader/st.caption/st.divider that
carry the tight, hand-set margins the Outputs tab already uses (its own
custom-HTML header/section-label/divider style) rather than Streamlit's
own default block spacing, which is considerably more generous. Exists so
Imports/Populations/Text can adopt the same visual density as Outputs
without every call site re-typing the same inline style.

Deliberately separate from core.ui.common.layout_css, which is a one-off
global CSS override scoped to the sidebar only (see that module's own
docstring) — these are per-element markdown substitutions used at
individual call sites, not a blanket rule applied to a whole content area
(Streamlit gives no reliable per-tab CSS selector to scope a global rule to
just these three tabs and not the others).

st.markdown still parses ordinary markdown syntax (backtick code spans,
**bold**, etc.) inside the surrounding HTML tags here, so existing caption
text using those doesn't need rewriting.
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
