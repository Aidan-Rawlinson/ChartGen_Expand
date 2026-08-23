"""
guidance.py
Per-tab guidance links, one URL per tab, maintained here rather than
scattered across the tabs. A blank entry renders nothing, so a tab with no
guidance page yet shows a plain title and no dead link.

Each tab renders its own link, because st.tabs() never reports which tab is
active into session_state: tab switching is pure client-side CSS, so a
single sidebar button that adapts to the active tab is not possible.

The title is raw HTML via render_tab_header rather than st.header(), so the
link can sit inline after it. That trades away st.header()'s anchor link.
Header colour comes from Streamlit's theme CSS; only margin is set inline.

guidance_link_html is exposed separately for outputs_tab.py, whose title is
a bespoke <h1> and which splices the fragment in itself.
"""

import streamlit as st

_GUIDANCE_PDF = (
    "https://rcigroupuk.sharepoint.com/sites/TBNIntranet/Shared%20Documents/"
    "Resource%20Library/Tools%20%26%20Templates/Internal%20Tools/ChartGen/"
    "Tab_Guide/ChartGen_Tab_Guidance.pdf"
)

GUIDANCE_URLS = {
    "imports":       f"{_GUIDANCE_PDF}#page=3",
    "populations":   f"{_GUIDANCE_PDF}#page=4",
    "select":        f"{_GUIDANCE_PDF}#page=5",
    "text":          f"{_GUIDANCE_PDF}#page=6",
    "running_order": f"{_GUIDANCE_PDF}#page=7",
    "charts":        f"{_GUIDANCE_PDF}#page=8",
    "outputs":       f"{_GUIDANCE_PDF}#page=9",
}


def guidance_link_html(tab_key: str) -> str:
    """HTML for the muted inline guidance link, or '' if no URL is configured for this tab."""
    url = GUIDANCE_URLS.get(tab_key, "")
    if not url:
        return ""
    return (
        f'&nbsp;&nbsp;<a href="{url}" target="_blank" '
        'style="color:#aaa; text-decoration:none;">'
        '<span style="font-size:11pt;">📖</span>'
        '<span style="font-size:5pt;"> </span>'
        '<span style="font-size:9pt; font-weight:400;">Guidance</span>'
        '</a>'
    )


def render_tab_header(title: str, tab_key: str, level: str = "h2"):
    """
    Render a tab's title with a muted inline guidance link following it
    (simulated padding via non-breaking spaces), or a plain title if no URL
    is configured for this tab yet. Use in place of st.header(title).
    """
    link_html = guidance_link_html(tab_key)
    st.markdown(f'<{level} style="margin:0 0 0.5em 0;">{title}{link_html}</{level}>',
                unsafe_allow_html=True)
