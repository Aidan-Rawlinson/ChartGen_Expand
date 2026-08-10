"""
cg_extracts.py
Resolves the CG_Extracts folder used by every Excel export/import
round-trip (Chart URL manifest, Chart Store, Output Table grids,
population tables) -- a single folder alongside the .cgw, replacing the
browser's own Downloads folder as the fixed destination/source for these
files. Created on first use if it doesn't already exist.

Excel export previously went through st.download_button and import through
st.file_uploader -- both browser-sandboxed widgets that give the server no
way to choose where a download lands or to default an upload dialog to a
particular folder. This module underpins the alternative: a direct
filesystem write on export, and a native OS picker (core.ui.common.pickers)
defaulted to this folder on import.

Reachable only from screens that require an already-saved .cgw (Imports,
Charts, Output Tables, Populations), so workfile_path is always expected to
be non-empty here -- no fallback for an unsaved workfile is provided.
"""

import os


def get_extracts_folder(workfile_path: str) -> str:
    """
    Return the CG_Extracts folder path alongside the given .cgw, creating
    it if it doesn't already exist.
    """
    workfile_dir = os.path.dirname(workfile_path)
    extracts_dir = os.path.join(workfile_dir, "CG_Extracts")
    os.makedirs(extracts_dir, exist_ok=True)
    return extracts_dir
