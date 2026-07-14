"""
new_workfile.py
Business logic for the New Workfile flow: fetching the project list for a
year, fetching submissions/organisations for a chosen project, building the
units table (including Region() assignment), and creating the saved .cgw.
Owns every API call and every rows-from-submissions transform for this flow;
the Streamlit form only collects inputs and displays results.
"""

from core.acquisition.toolkit_nhs.api_client import get_projects, get_submissions, get_organisations
from core.workfile.state.workfile_file import new_workfile as _create_workfile_file, write_lock, save_workfile


def list_projects_for_year(year: int, token: str) -> dict:
    """Return {project_name: project_id} for the given year."""
    project_list = get_projects(year, token)
    return {p["project_name"]: p["project_id"] for p in project_list}


def build_units_from_submissions(submission_rows: list, org_rows: list) -> list:
    """
    Build the units table from raw submission and organisation API rows.
    Resolves Region() onto each unit from the matching organisation.
    """
    org_lookup = {r["organisation_id"]: r for r in org_rows}
    rows_out = []
    for row in submission_rows:
        services = row.get("services", [])
        org = org_lookup.get(row["organisation_id"], {})
        rows_out.append({
            "unit_id":                  row["submission_id"],
            "unit_code":                row["submission_code"],
            "unit_name":                row["submission_name"],
            "submission_year":          row.get("submission_year", ""),
            "project_id":               row.get("project_id", ""),
            "project_name":             row.get("project_name", ""),
            "organisation_id":          row["organisation_id"],
            "organisation_name":        row["organisation_name"],
            "submission_service_count": row.get("submission_service_count", ""),
            "response_count":           row.get("response_count", ""),
            "submission_level":         row.get("submission_level", ""),
            "service_item_ids":   "|".join(str(s["service_item_id"])   for s in services),
            "service_item_names": "|".join(str(s["service_item_name"]) for s in services),
            "service_response_counts": "|".join(str(s["response_count"]) for s in services),
            "Region()":                 org.get("region_name", ""),
        })
    return rows_out


def create_new_workfile(workfile_path: str, workfile_name: str, year: int,
                         project_id, project_name: str, token: str, username: str):
    """
    Fetch submissions and organisations for the given project/year, build the
    units table, create the WorkfileState, write the lock, and save it to disk.
    Raises ValueError if no submissions are found for the project/year.
    Returns the saved WorkfileState.
    """
    org_rows = get_organisations(int(year), token)
    submission_rows = get_submissions(int(project_id), int(year), token)
    if not submission_rows:
        raise ValueError("No submissions found for this project and year.")

    ws_new = _create_workfile_file(workfile_path, workfile_name)
    ws_new.settings = {
        "year":                    str(year),
        "project_id":              str(project_id),
        "project_name":            project_name,
        "cleaned_template_path":   "",
        "ppt_template_path":       "",
        "selected_unit_id":        "",
        "batch_cursor":            "0",
    }
    ws_new.units = build_units_from_submissions(submission_rows, org_rows)
    ws_new.locked_by = username

    write_lock(workfile_path, username)
    save_workfile(ws_new, username)

    return ws_new
