"""
population_tables.py
Building and maintaining population-level tables (nhs_organisations,
submissions_{year}_{project_id}) from the NHS toolkit API. Lives in
acquisition, not workfile.setup — this is "pull and normalise NHS toolkit
data", the same kind of concern as api_client/transformers/cache_writer, not
a workfile-creation concern. That's also what lets fetch.py (same package)
call ensure_population_tables directly: acquisition code must never depend
on workfile.setup (one-way dependency rule, Architecture §2), and this used
to sit in workfile.setup, which is exactly why it had to move.

Every population-level table shares the same spine — unit_id, unit_code,
unit_name, soft_parents, plus any number of Name() peer-group columns — so
that any table can be treated the same way regardless of what it holds.
Table-specific detail (nhs_code, submission counts, project_id, etc.) is not
carried onto these tables; only the shared spine survives for now.
"""

from core.acquisition.toolkit_nhs.api_client import get_submissions, get_organisations
from core.acquisition.toolkit_nhs.table_naming import submissions_table_name
from core.shared.infrastructure.soft_parents import format_soft_parents

ORGANISATIONS_TABLE = "nhs_organisations"


def build_organisations_table(org_rows: list) -> list:
    """
    Build the nhs_organisations table from raw organisation API rows, onto
    the shared spine. unit_code is populated from nhs_code where available,
    "N/A" otherwise. soft_parents is empty — organisations have no
    soft-parent link yet.
    """
    rows_out = []
    for org in org_rows:
        nhs_code = str(org.get("nhs_code", "") or "").strip()
        rows_out.append({
            "unit_id":      org["organisation_id"],
            "unit_code":    nhs_code if nhs_code else "N/A",
            "unit_name":    org.get("organisation_name", ""),
            "soft_parents": "",
            "Region()":     org.get("region_name", ""),
        })
    return rows_out


def build_submissions_table(submission_rows: list, org_rows: list) -> list:
    """
    Build a submissions table from raw submission API rows, onto the shared
    spine. Resolves Region() from the matching organisation, and records the
    organisation link as a soft_parents entry rather than a bespoke
    organisation field.
    """
    org_lookup = {r["organisation_id"]: r for r in org_rows}
    rows_out = []
    for row in submission_rows:
        org = org_lookup.get(row["organisation_id"], {})
        rows_out.append({
            "unit_id":      row["submission_id"],
            "unit_code":    row["submission_code"],
            "unit_name":    row["submission_name"],
            "soft_parents": format_soft_parents({ORGANISATIONS_TABLE: [row["organisation_id"]]}),
            "Region()":     org.get("region_name", ""),
        })
    return rows_out


def add_project_tables(workfile_state, year: int, project_id, token: str):
    """
    Fetch submissions and organisations for one project/year and add its
    population tables to an already-existing WorkfileState — mutates
    workfile_state.tables/table_order in place and marks it dirty. Does NOT
    save; the caller saves afterwards, same as any other in-session edit.
    Raises ValueError if no submissions are found for the project/year.

    nhs_organisations is merged, not overwritten, if it already exists: this
    project's organisations are built in memory first, then only the ones
    not already present (by unit_id — organisation_id — the source of
    truth for identity) are appended to the existing table. Existing rows
    are left untouched. No separate step re-resolves Region() across the
    merged table: Region() is a straight per-organisation value copied from
    the API's region_name at build time, not something computed from the
    rest of the table, so every row — old or newly appended — already
    carries its own correct value the moment it's built. If Region() (or any
    future peer-group column) ever became something resolved *from* the
    full table rather than handed to us per-organisation, this assumption
    would need revisiting.
    """
    org_rows = get_organisations(int(year), token)
    submission_rows = get_submissions(int(project_id), int(year), token)
    if not submission_rows:
        raise ValueError("No submissions found for this project and year.")

    # The organisations table is built from the submissions table, not the
    # other way round — it only carries organisations actually referenced by
    # a submission, not every organisation that exists for the year.
    referenced_org_ids = {row["organisation_id"] for row in submission_rows}
    org_rows = [o for o in org_rows if o["organisation_id"] in referenced_org_ids]

    sub_table_name = submissions_table_name(year, project_id)
    workfile_state.tables[sub_table_name] = build_submissions_table(submission_rows, org_rows)

    new_org_rows = build_organisations_table(org_rows)
    existing_org_rows = workfile_state.tables.get(ORGANISATIONS_TABLE)
    if existing_org_rows:
        existing_ids = {r["unit_id"] for r in existing_org_rows}
        merged_org_rows = list(existing_org_rows)
        for row in new_org_rows:
            if row["unit_id"] not in existing_ids:
                merged_org_rows.append(row)
        workfile_state.tables[ORGANISATIONS_TABLE] = merged_org_rows
    else:
        workfile_state.tables[ORGANISATIONS_TABLE] = new_org_rows

    # table_order[0] is the master table — drives the reporting unit picker
    # and the batch loop. Appending (rather than assuming an empty list)
    # means this puts the first project's submissions table in the master
    # position naturally, without special-casing "is this the first call".
    for table_name in (sub_table_name, ORGANISATIONS_TABLE):
        if table_name not in workfile_state.table_order:
            workfile_state.table_order.append(table_name)

    workfile_state.dirty = True
    return workfile_state


def ensure_population_tables(workfile_state, year, project_id, token: str) -> bool:
    """
    The trigger point: given a chart's own year/project_id (identified
    during an individual chart pull — see fetch.py), check whether that
    project's submissions table already exists on this workfile. If it
    does, do nothing. If it doesn't, build it (and nhs_organisations) via
    add_project_tables before the chart's own fetch continues.

    Returns True if tables were just created, False if they already existed.
    Safe to call repeatedly across different projects on the same workfile —
    add_project_tables merges into nhs_organisations rather than overwriting
    it when it already exists.
    """
    table_name = submissions_table_name(year, project_id)
    if table_name in workfile_state.tables:
        return False
    add_project_tables(workfile_state, year, project_id, token)
    return True
