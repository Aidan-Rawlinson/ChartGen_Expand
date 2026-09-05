"""
settings_tab.py
Workfile-level settings. Currently one: the default font every chart and
table renders in.

The font is a stored user choice, saved in this workfile's settings, so
changing it is a setting rather than a code edit. The picker offers only the
families ChartGen ships in its fonts/ folder, because those are the ones it
also installs, and so the ones a colleague opening this workfile is
guaranteed to have.

Adding a font is dropping its files and its licence text into a subfolder of
fonts/. Nothing here needs editing for it to appear.

The install mechanics and the Windows-side status live in
chartgen.session_shell.lifecycle.font_startup.
"""

import streamlit as st

from chartgen.session_shell.lifecycle.font_startup import (
    font_status, install_missing_fonts, per_user_fonts_dir,
)
from chartgen.shared.infrastructure.bundled_fonts import bundled_family_names, fonts_dir
from chartgen.ui.common.compact_layout import tight_caption, tight_divider, tight_subheader
from chartgen.ui.common.flash import queue_flash
from chartgen.ui.common.guidance import render_tab_header
from chartgen.workfile.state.session_state import settings, save_settings


def render_settings_tab():
    render_tab_header("Settings", "settings")

    _render_default_font()
    tight_divider()
    _render_bundled_fonts()


def _render_default_font():
    tight_subheader("Default font")
    tight_caption(
        "Every chart and table renders in this font. It is saved in this "
        "workfile, so a colleague opening it gets the same typography."
    )

    families = bundled_family_names()
    saved = settings().get("default_font", "")

    if not families:
        st.error(
            f"No fonts found in {fonts_dir()}. Charts and tables cannot render "
            "until at least one font is available. Add a font family as a "
            "subfolder there, with its font files and the licence text that "
            "came with them."
        )
        return

    index = families.index(saved) if saved in families else None
    chosen = st.selectbox(
        "Default font", options=families, index=index,
        placeholder="Select a font…", key="set_default_font",
    )

    if chosen and chosen != saved:
        s = settings()
        s["default_font"] = chosen
        save_settings(s)

    # A workfile can name a font that is no longer bundled — it was saved
    # against an earlier fonts/ folder, or hand-edited. Said plainly here
    # rather than left to fail at the first render.
    if saved and saved not in families:
        st.warning(
            f"This workfile's saved default font (\"{saved}\") is not one "
            "ChartGen currently ships. Renders will stop with an error until "
            "a font from the list above is chosen."
        )

    if not chosen:
        st.warning(
            "No default font is set for this workfile. Renders will stop with "
            "an error until one is chosen."
        )
        return

    row = next((r for r in font_status() if r["family"] == chosen), None)
    if row and not row["has_bold"]:
        st.warning(
            f"\"{chosen}\" has no bold face, so text drawn in bold will come "
            "out at regular weight with nothing reporting it. This is what a "
            "variable font produces: matplotlib reads only its default weight "
            "and cannot reach the rest of the weight axis. Add the static "
            "Bold file for this family to fix it."
        )


def _render_bundled_fonts():
    tight_subheader("Bundled fonts")
    tight_caption(
        "Fonts ChartGen ships and installs for you. Installing them into "
        "Windows is what lets PowerPoint display chart text correctly, since "
        "chart text stays real text rather than being flattened to outlines."
    )

    rows = font_status()
    if not rows:
        tight_caption(f"None. Looked in {fonts_dir()}.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame([
            {
                "Font":                 row["family"],
                "Faces":                ", ".join(face["style"] for face in row["faces"]),
                "Installed in Windows": "Yes" if row["installed"] else "No",
                "Bold available":       "Yes" if row["has_bold"] else "No",
                "Licence file":         ", ".join(row["licence_files"]) or "Missing",
            }
            for row in rows
        ]),
        use_container_width=True, hide_index=True,
    )

    not_installed = [row["family"] for row in rows if not row["installed"]]
    if not_installed:
        st.warning(
            "Not installed in Windows: " + ", ".join(not_installed) + ". Charts "
            "and tables will still render correctly, because ChartGen loads "
            "these fonts itself, but PowerPoint will substitute a different "
            "font when displaying them. Use the button below to install them."
        )

    missing_licence = [row["family"] for row in rows if not row["licence_files"]]
    if missing_licence:
        st.warning(
            "No licence file found beside: " + ", ".join(missing_licence) + ". "
            "Most font licences, including the SIL Open Font License that "
            "covers most Google Fonts, require the licence text to be "
            "distributed with the font. Nothing is blocked, but the file "
            "should be added to that font's folder."
        )

    if st.button("Check and install bundled fonts", key="set_install_fonts"):
        problems = install_missing_fonts()
        if problems:
            for problem in problems:
                st.error(problem)
        else:
            queue_flash("Bundled fonts checked. Nothing missing.")
            st.rerun()

    tight_caption(f"Installed for the current user only, in {per_user_fonts_dir()}.")
