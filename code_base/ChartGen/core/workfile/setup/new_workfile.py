"""
new_workfile.py
The New Workfile flow's file-creation half only: create_new_workfile makes
a blank .cgw with no project data whatsoever — no NHS toolkit involvement.

Population tables are a separate, acquisition-layer concern now — see
core.acquisition.toolkit_nhs.population_tables (add_project_tables,
ensure_population_tables). Nothing here knows tables exist; nothing there
knows a workfile might be brand new.
"""

from core.acquisition.toolkit_nhs.api_client import get_projects
from core.workfile.state.workfile_file import new_workfile as _create_workfile_file, write_lock, save_workfile


def list_projects_for_year(year: int, token: str) -> dict:
    """Return {project_name: project_id} for the given year."""
    project_list = get_projects(year, token)
    return {p["project_name"]: p["project_id"] for p in project_list}


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
    """
    ws_new = _create_workfile_file(workfile_path, workfile_name)
    ws_new.settings = {
        "description":             description,
        "cleaned_template_path":   "",
        "ppt_template_path":       "",
        "selected_unit_id":        "",
        "batch_cursor":            "0",
    }
    ws_new.locked_by = username

    write_lock(workfile_path, username)
    save_workfile(ws_new, username)

    return ws_new
