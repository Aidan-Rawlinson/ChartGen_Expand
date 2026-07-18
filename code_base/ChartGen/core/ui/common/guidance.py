"""
guidance.py
Per-tab guidance links — one page-length guidance URL per tab, opened in a
new browser tab. Exists because st.tabs() never reports which tab is
active into session_state (tab switching is pure client-side CSS/JS), so a
single "smart" sidebar button that adapts to the active tab isn't possible
(Current_State, "Open current sheet's guidance PDF" note). Each tab renders
its own link from inside its own render function instead — Streamlit only
displays that tab's content when it's the one open, so no active-tab
detection is needed at all, and the sidebar/tab-agnostic design principle
(Functional Spec Section 3.1) is untouched.

The link is rendered inline after the tab's own title, muted (small, grey,
no underline) rather than as a button, so it reads as a quiet footnote
rather than a competing action — this means the title itself is written as
raw HTML (via render_tab_header) rather than st.header(), trading away
st.header()'s hover-to-reveal "#" anchor link for the inline placement.
Header text colour still comes from Streamlit's own theme CSS (only
margin is set inline here), so light/dark mode is unaffected; the link's
grey is hardcoded, since it's meant to look the same regardless of theme.

guidance_link_html is exposed separately (not just render_tab_header) for
outputs_tab.py, whose title is a bespoke sized <h1> rather than a plain
header — it splices the fragment into its own markdown call directly.

URLs are maintained here, in one place, rather than scattered across each
tab's own code. Blank entries render nothing, so a tab without its
guidance page written yet shows a plain title with no dead link.
"""

import streamlit as st

GUIDANCE_URLS = {
    "details":       "https://www.bbc.co.uk",
    "config":        "https://www.bbc.co.uk",
    "imports":       "https://www.bbc.co.uk",
    "populations":   "https://www.bbc.co.uk",
    "select":        "https://www.bbc.co.uk",
    "text":          "https://www.bbc.co.uk",
    "running_order": "https://www.bbc.co.uk",
    "charts":        "https://www.bbc.co.uk",
    "outputs":       "https://www.bbc.co.uk",
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
