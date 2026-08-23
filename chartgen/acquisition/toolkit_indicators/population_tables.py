"""
population_tables.py
Builds and maintains the Indicators toolkit's own population table,
submissions_timeseries_{project_id}.

This merges on every fetch, unlike the NHS side's build-once model. Two
reasons: one report fetch returns every period at once, so even the first
build has to union submissions across every period in that response; and
submissions genuinely drop in and out of this toolkit over time, so an
established table has to reconcile on every fetch. Same append-by-unit_id,
never-overwrite rule as nhs_organisations, just run every time.

soft_parents links each submission to nhs_organisations:{unit_id} through a
live org_id_map (ics organisation_id to nhs unit_id), sourced fresh on every
fetch from this project's own /projects/{id}/submissions response. The two
databases' organisation id spaces do not match, so the Indicators
organisation_id cannot be used directly.

A submission whose organisation_id has no entry in org_id_map, or an
explicit None, is still added, with no soft_parents link and a blank
Region(). merge_timeseries_population reports that back to fetch.py as a
boolean, so one warning is surfaced per fetch run rather than per
submission.

A resolved organisation not already in nhs_organisations is enriched from
toolkit_nhs.api_client.get_organisations first. This toolkit has no year of
its own, so that lookup uses the current calendar year. Falls back to the
Indicators response's own name and code with a blank Region() only if the id
is genuinely absent from that year's list, for example a retired
organisation.

Region() on the submission row is resolved from that same now-enriched
data, not from whatever nhs_organisations held before this call, so a
newly-discovered organisation gets its correct Region() immediately.

unit_name comes from submission_name_map, the same response's real
submissionName, falling back to anonSubmissionCode only if absent.
unit_code stays anonSubmissionCode, so the two fields differ.
"""

from datetime import datetime

from chartgen.acquisition.toolkit_nhs.api_client import get_organisations as get_nhs_organisations
from chartgen.shared.infrastructure.soft_parents import format_soft_parents

TIMESERIES_TABLE_PREFIX = "submissions_timeseries_"
ORGANISATIONS_TABLE = "nhs_organisations"


def _table_name(project_id) -> str:
    from chartgen.acquisition.toolkit_indicators.table_naming import submissions_timeseries_table_name
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


def merge_timeseries_population(
    workfile_state, project_id, report_data: dict, *,
    token: str, org_id_map: dict, submission_name_map: dict,
) -> tuple[bool, bool]:
    """
    Merge every submission referenced in one report's response into
    submissions_timeseries_{project_id} (created if it doesn't exist yet),
    and merge any newly-resolved organisation into nhs_organisations.
    Append by unit_id only — existing rows are never overwritten. Mutates
    workfile_state in place and marks it dirty. Does NOT save.

    org_id_map: {ics organisation_id (str) -> nhs unit_id (str) or None},
    sourced live per-project by fetch.py — see module docstring.
    submission_name_map: {submissionId (str) -> submissionName}, same
    source, supplies unit_name.

    token is required to enrich newly-discovered organisations against the
    NHS organisations endpoint (see module docstring) — only used if at
    least one submission this call resolves to an organisation not already
    in nhs_organisations.

    Returns (changed, had_unmapped):
    - changed: True if any new rows were added to either table.
    - had_unmapped: True if one or more submissions in this response
      referenced an organisation_id with no entry (or an explicit None) in
      org_id_map — those submissions are still added, with no soft_parents
      link and Region() left blank (see module docstring). The caller
      (fetch.py) is responsible for surfacing a single end-of-fetch warning
      built from this flag, not for reporting per-submission detail.
    """
    submissions = extract_submissions(report_data)
    table_name = _table_name(project_id)

    existing_sub_rows = workfile_state.tables.get(table_name, [])
    existing_sub_ids = {r["unit_id"] for r in existing_sub_rows}

    existing_org_rows = workfile_state.tables.get(ORGANISATIONS_TABLE, [])
    existing_org_ids = {r["unit_id"] for r in existing_org_rows}
    org_rows_by_id = {r["unit_id"]: r for r in existing_org_rows}

    new_sub_rows = []
    new_org_rows = []
    had_unmapped = False

    # First pass: resolve every submission's organisation_id and note which
    # resolved ids are genuinely new to nhs_organisations. Region() has to
    # be known before any submission row is built, not discovered
    # afterward, so enrichment happens before the second pass below.
    resolved = []
    to_enrich = set()
    first_sub_for_org = {}
    for sub in submissions:
        raw_org_id = sub["organisation_id"]
        org_id = org_id_map.get(str(raw_org_id)) if raw_org_id is not None else None
        if org_id is None:
            had_unmapped = True
        elif org_id not in existing_org_ids:
            to_enrich.add(org_id)
            first_sub_for_org.setdefault(org_id, sub)
        resolved.append((sub, org_id))

    if to_enrich:
        # Current calendar year: this data has no year of its own, so the
        # NHS organisations lookup is queried against now.
        nhs_orgs = {str(o["organisation_id"]): o for o in get_nhs_organisations(datetime.now().year, token)}
        for org_id in to_enrich:
            nhs_org = nhs_orgs.get(org_id)
            if nhs_org:
                new_row = {
                    "unit_id":      org_id,
                    "unit_code":    str(nhs_org.get("nhs_code") or "N/A"),
                    "unit_name":    nhs_org.get("organisation_name", ""),
                    "soft_parents": "",
                    "Region()":     nhs_org.get("region_name", ""),
                }
            else:
                # Resolved via org_id_map but absent from this year's NHS
                # organisations list, for example a retired organisation.
                # Fall back to the Indicators response's own values.
                fallback_sub = first_sub_for_org[org_id]
                new_row = {
                    "unit_id":      org_id,
                    "unit_code":    fallback_sub["organisation_code"] or "N/A",
                    "unit_name":    fallback_sub["organisation_name"],
                    "soft_parents": "",
                    "Region()":     "",
                }
            new_org_rows.append(new_row)
            org_rows_by_id[org_id] = new_row

    for sub, org_id in resolved:
        sub_id = str(sub["submission_id"])
        if sub_id not in existing_sub_ids:
            new_sub_rows.append({
                "unit_id":      sub_id,
                "unit_code":    sub["anon_submission_code"],
                "unit_name":    submission_name_map.get(sub_id) or sub["anon_submission_code"],
                "soft_parents": format_soft_parents({ORGANISATIONS_TABLE: [org_id]}) if org_id else "",
                "Region()":     org_rows_by_id.get(org_id, {}).get("Region()", "") if org_id else "",
            })
            existing_sub_ids.add(sub_id)

    if not new_sub_rows and not new_org_rows:
        return False, had_unmapped

    if new_sub_rows:
        workfile_state.tables[table_name] = existing_sub_rows + new_sub_rows
        if table_name not in workfile_state.table_order:
            workfile_state.table_order.append(table_name)

    if new_org_rows:
        workfile_state.tables[ORGANISATIONS_TABLE] = existing_org_rows + new_org_rows
        if ORGANISATIONS_TABLE not in workfile_state.table_order:
            workfile_state.table_order.append(ORGANISATIONS_TABLE)

    workfile_state.dirty = True
    return True, had_unmapped
