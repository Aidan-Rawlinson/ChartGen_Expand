"""
concurrency.py
Lock-state resolution — mechanics only. Extracted from the Open Workfile
dialog callback, where lock classification and the Open/Open Read-Only
actions were previously fused with the dialog's own rendering.
"""

from core.workfile.state.workfile_file import open_workfile, write_lock


def classify_lock_state(info: dict, current_user: str) -> str:
    """
    Classify a workfile's lock info relative to current_user.
    Returns one of the three states named in Functional Spec Section 5:
      'unlocked'         — not marked open by anyone
      'locked_by_self'   — marked open by the current user (stale session or
                            still open elsewhere under this account)
      'locked_by_other'  — marked open by a different user
    """
    locked_by = (info.get("locked_by") or "").strip()
    if not locked_by:
        return "unlocked"
    if locked_by == current_user:
        return "locked_by_self"
    return "locked_by_other"


def open_normal(path: str, current_user: str):
    """Claim the lock and open the workfile as a normal editable session."""
    write_lock(path, current_user)
    ws_opened = open_workfile(path)
    ws_opened.locked_by = current_user
    ws_opened.read_only = False
    return ws_opened


def open_read_only(path: str):
    """Open the workfile without claiming the lock."""
    ws_opened = open_workfile(path)
    ws_opened.read_only = True
    return ws_opened
