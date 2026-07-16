"""
population_tables.py
Building and maintaining the Indicators toolkit's own population table
(submissions_timeseries_{project_id}) — deliberately NOT the same trigger
model as toolkit_nhs/population_tables.py's ensure_population_tables.

Two things make the NHS "build once, then no-op forever" model wrong here:
1. A single Indicators report fetch already returns every period at once —
   the first build has to union submissions across every period in that one
   response, not just whatever's present "now".
2. Submissions genuinely drop in and out of the Indicators toolkit over
   time (confirmed) — so even after the table exists, a later fetch (a
   refresh, or a different metric under the same project) can reveal
   submissions the table doesn't have yet. Every fetch has to reconcile,
   not just the first.

So this module merges on every call, the same append-by-unit_id, no-
overwrite rule nhs_organisations already uses for cross-project merging —
just applied on every fetch here, not only the first.

soft_parents links each submission row to nhs_organisations:{organisation_id}
— reusing the existing NHS organisations table on the assumption that
organisation ids match across both APIs (confirmed as an assumption to
revisit if it turns out to be wrong, not a verified fact). If a referenced
organisation isn't already in nhs_organisations, it's added — using
organisationName/organisationCode from the Indicators response itself, no
extra API call needed — so soft_parents never points at a row that doesn't
exist.

Region() is carried on every submissions_timeseries row too, keeping the
identical-headers convention every population table follows — sourced the
same way the NHS side sources it (a lookup against the organisation row,
not anything from the chart data itself), just looked up against whatever's
already in nhs_organisations at merge time rather than a region_name field
the Indicators API happens to supply (it doesn't). Left blank only when the
organisation itself is new to nhs_organisations this same fetch, with
nothing yet to copy from.
"""

from core.shared.infrastructure.soft_parents import format_soft_parents

TIMESERIES_TABLE_PREFIX = "submissions_timeseries_"
ORGANISATIONS_TABLE = "nhs_organisations"


def _table_name(project_id) -> str:
    from core.acquisition.toolkit_indicators.table_naming import submissions_timeseries_table_name
    return submissions_timeseries_table_name(project_id)


def extract_submissions(report_data: dict) -> list:
    """
    Union every (submission_id, anon_submission_code, organisation_id) tuple
    seen across every period in one report's availableDates — a single
    fetch response can itself span the whole population's history, so this
    has to look across every period, not just the most recent one.
    De-duplicated by submission_id, first occurrence wins (identity fields
    shouldn't differ between periods for the same submission).
    """
    seen = {}
    for period in report_data.get("availableDates", []):
        for org in period.get("organisationList", []):
            org_id = org.get("organisationId")
            for sub in org.get("submissionData", []):
                sub_id = sub.get("submissionId")
                if sub_id is None or sub_id in seen:
                    continue
                seen[sub_id] = {
                    "submission_id":       sub_id,
                    "anon_submission_code": sub.get("anonSubmissionCode", ""),
                    "organisation_id":      org_id,
                    "organisation_code":    org.get("organisationCode", ""),
                    "organisation_name":    org.get("organisationName", ""),
                }
    return list(seen.values())


def merge_timeseries_population(workfile_state, project_id, report_data: dict) -> bool:
    """
    Merge every submission referenced in one report's response into
    submissions_timeseries_{project_id} (created if it doesn't exist yet),
    and merge any newly-seen organisation into nhs_organisations. Append by
    unit_id only — existing rows are never overwritten. Mutates
    workfile_state in place and marks it dirty. Does NOT save.

    Returns True if any new rows were added to either table, False if
    everything was already present.
    """
    submissions = extract_submissions(report_data)
    table_name = _table_name(project_id)

    existing_sub_rows = workfile_state.tables.get(table_name, [])
    existing_sub_ids = {r["unit_id"] for r in existing_sub_rows}

    existing_org_rows = workfile_state.tables.get(ORGANISATIONS_TABLE, [])
    existing_org_ids = {r["unit_id"] for r in existing_org_rows}
    org_lookup = {r["unit_id"]: r for r in existing_org_rows}

    new_sub_rows = []
    new_org_rows = []
    seen_new_org_ids = set()

    for sub in submissions:
        sub_id = str(sub["submission_id"])
        org_id = str(sub["organisation_id"]) if sub["organisation_id"] is not None else ""

        if sub_id not in existing_sub_ids:
            new_sub_rows.append({
                "unit_id":      sub_id,
                "unit_code":    sub["anon_submission_code"],
                "unit_name":    sub["anon_submission_code"],
                "soft_parents": format_soft_parents({ORGANISATIONS_TABLE: [org_id]}) if org_id else "",
                # Same source as the NHS side (a lookup against the
                # organisation row, not chart data) — just looked up here
                # against nhs_organisations directly, since the Indicators
                # API itself supplies no region_name field.
                "Region()":     org_lookup.get(org_id, {}).get("Region()", ""),
            })
            existing_sub_ids.add(sub_id)

        if org_id and org_id not in existing_org_ids and org_id not in seen_new_org_ids:
            new_org_rows.append({
                "unit_id":      org_id,
                "unit_code":    sub["organisation_code"] or "N/A",
                "unit_name":    sub["organisation_name"],
                "soft_parents": "",
                "Region()":     "",  # not supplied by the Indicators API
            })
            seen_new_org_ids.add(org_id)

    if not new_sub_rows and not new_org_rows:
        return False

    if new_sub_rows:
        workfile_state.tables[table_name] = existing_sub_rows + new_sub_rows
        if table_name not in workfile_state.table_order:
            workfile_state.table_order.append(table_name)

    if new_org_rows:
        workfile_state.tables[ORGANISATIONS_TABLE] = existing_org_rows + new_org_rows
        if ORGANISATIONS_TABLE not in workfile_state.table_order:
            workfile_state.table_order.append(ORGANISATIONS_TABLE)

    workfile_state.dirty = True
    return True
