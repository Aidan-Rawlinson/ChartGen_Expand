"""
save_as.py
Business logic for Save Workfile As: copies the cleaned template alongside
the new .cgw (renamed to match), transfers/releases the advisory lock, and
saves the workfile under the new path. Owns the read-only-session-must-
choose-a-different-folder rule too — a business rule about the lock, not a
widget concern. The Streamlit form only collects the new path (via a native
Save dialog, which handles its own overwrite confirmation); everything here
is delegated from there.
"""

import os
import shutil

from core.workfile.state.workfile_file import save_workfile, write_lock, clear_lock


def is_same_as_original_folder(ws_cur, folder: str) -> bool:
    """
    Return True if folder is the same folder the read-only session's workfile
    was opened from. Save As from a Read-Only session must target a
    different folder, to avoid two workfiles sharing one outputs folder.
    """
    original_folder = os.path.dirname(ws_cur.workfile_path)
    return os.path.abspath(folder) == os.path.abspath(original_folder)


def save_as(ws_cur, new_workfile_path: str, new_name: str, username: str):
    """
    Copy the cleaned template alongside the new .cgw, write the lock at the
    new location, save the workfile there, and release the lock on the old
    file if this session held it.

    Mutates and returns ws_cur.
    """
    s = ws_cur.settings
    was_read_only = ws_cur.read_only
    old_workfile_path = ws_cur.workfile_path
    old_template_path = (s.get("cleaned_template_path") or "").strip()

    # Copy the cleaned template alongside the new .cgw, renamed to match
    if old_template_path and os.path.exists(old_template_path):
        new_template_path = os.path.join(os.path.dirname(new_workfile_path), f"{new_name}.pptx")
        shutil.copyfile(old_template_path, new_template_path)
        s["cleaned_template_path"] = new_template_path
        s["ppt_template_path"] = new_template_path

    ws_cur.workfile_name = new_name
    write_lock(new_workfile_path, username)
    ws_cur.locked_by = username
    ws_cur.read_only = False
    save_workfile(ws_cur, username, target_path=new_workfile_path)

    # Release the lock on the old file — only if this session held it.
    # A read-only session never claimed the old file's lock, so it must
    # never clear one that may still genuinely belong to someone else.
    if not was_read_only:
        if old_workfile_path and old_workfile_path != new_workfile_path and os.path.exists(old_workfile_path):
            try:
                clear_lock(old_workfile_path)
            except Exception:
                pass

    return ws_cur
