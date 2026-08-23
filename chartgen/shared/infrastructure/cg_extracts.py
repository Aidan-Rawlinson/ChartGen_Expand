"""
cg_extracts.py
Resolves the CG_Extracts folder alongside the .cgw, used by every Excel
export/import round-trip. Created on first use.

Callers are reached only from screens requiring an already-saved .cgw, so
workfile_path is expected to be non-empty. There is no unsaved-workfile
fallback.
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
