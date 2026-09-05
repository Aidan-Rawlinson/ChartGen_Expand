"""
new_workfile.py
The New Workfile flow's file-creation half only: create_new_workfile makes
a blank .cgw with no project data whatsoever — no NHS toolkit involvement.

Population tables are an acquisition-layer concern. Nothing here knows they
exist, and nothing there knows a workfile might be brand new. Keep it that
way.
"""

from chartgen.shared.infrastructure.bundled_fonts import NEW_WORKFILE_FONT
from chartgen.workfile.state.workfile_file import new_workfile as _create_workfile_file, write_lock, save_workfile


def create_new_workfile(workfile_path: str, workfile_name: str, description: str, username: str):
    """
    Create a blank workfile: no project, no population tables, no NHS
    toolkit involvement of any kind. Just the file, the user-facing
    description of what it's for, and the session-level settings scaffold.
    Writes the lock and saves. Returns the saved WorkfileState with empty
    tables/table_order.

    description is for the person, not the system — shown in the app header
    for as long as this workfile is open (see app.py). It plays no part in
    naming the file, resolving tables, or anything else structural.

    default_font starts at NEW_WORKFILE_FONT so a brand-new workfile can
    render straight away. It is a starting value the user changes on the
    Settings tab, not a fallback: nothing re-reads it if a workfile's own
    value is later missing or names a font this machine does not have.
    """
    ws_new = _create_workfile_file(workfile_path, workfile_name)
    ws_new.settings = {
        "description":             description,
        "cleaned_template_path":   "",
        "ppt_template_path":       "",
        "selected_unit_id":        "",
        "batch_cursor":            "0",
        "default_font":            NEW_WORKFILE_FONT,
    }
    ws_new.locked_by = username

    write_lock(workfile_path, username)
    save_workfile(ws_new, username)

    return ws_new
