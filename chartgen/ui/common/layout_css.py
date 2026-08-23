"""
layout_css.py
One-off CSS injection to tighten pieces of Streamlit's own default spacing
that no native Streamlit parameter controls:

1. The sidebar's own reserved header bar (data-testid="stSidebarHeader"),
   which houses the collapse-arrow button — confirmed via browser
   inspection to be the actual source of the large gap above the
   "ChartGen" heading in the sidebar.
2. The default vertical gap Streamlit applies between stacked elements
   inside a vertical block, scoped to the sidebar only (not the main
   content area) via the stSidebar ancestor selector, so this doesn't
   affect chart-tab spacing etc.

Do not add a padding-top rule on the main block-container: it clips the
"ChartGen" title against Streamlit's fixed header bar.

A narrow, deliberate exception to keeping the UI free of custom CSS, because
this spacing is not reachable through Streamlit's own widget parameters. If
a Streamlit upgrade changes these selectors, this is the one place to
update.
"""

import streamlit as st

_CSS = """
<style>
/* The sidebar's own reserved header bar (holds the collapse-arrow button)
   — the source of the large gap above the "ChartGen" heading in the
   sidebar. */
div[data-testid="stSidebarHeader"],
section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
    min-height: 0 !important;
    height: auto !important;
}

/* The wrapper around everything placed into the sidebar via st.sidebar —
   distinct from stSidebarHeader above (which is just the collapse-arrow
   bar) — carries its own default top padding on top of the header's. */
div[data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    padding-top: 0.25rem !important;
}

/* The header's height is actually forced by this empty spacer div (reserved
   for st.logo(), which this app doesn't use), not by the header itself —
   confirmed via the Computed panel: overriding height/padding on
   stSidebarHeader alone had no effect until this was also removed. */
div[data-testid="stLogoSpacer"],
section[data-testid="stSidebar"] div[data-testid="stLogoSpacer"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0.35rem !important;
}
</style>
"""


def inject_layout_css():
    st.markdown(_CSS, unsafe_allow_html=True)
