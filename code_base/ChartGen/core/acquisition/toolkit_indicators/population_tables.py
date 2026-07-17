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

soft_parents links each submission row to nhs_organisations:{unit_id} —
translated via a live org_id_map (ics organisation_id -> nhs unit_id),
sourced fresh on every fetch from this project's own
/projects/{id}/submissions response (see api_client.get_project_submissions_data
and fetch.py) — not the Indicators API's own organisation_id directly
(confirmed: the two databases' organisation id spaces do not match), and
NOT a static CSV extract either (retired — a live per-project mapping needs
no manual upkeep and can't go stale). If org_id_map has no entry — or an
explicit None — for a submission's organisation_id, the submission is
still added, but with no soft_parents link and Region() left blank — see
"Unmapped organisations" below.

If a referenced organisation IS resolved but isn't already in
nhs_organisations, it is enriched from the NHS organisations endpoint
(toolkit_nhs.api_client.get_organisations — the same call toolkit_nhs
itself uses to source Region(), reused here rather than duplicated, the
same precedent as sharing get_token, see Architecture Decision 10) before
its row is built, rather than being built from the Indicators response's
own organisation_name/organisation_code with a blank Region(). The
Indicators toolkit has no year of its own (periods only, see Decision 10),
so this lookup is queried against the current calendar year as the best
available stand-in — confirmed as the intended behaviour, not a guess.
Falls back to the Indicators response's own name/code with a blank
Region() only if the resolved id genuinely isn't present in that year's
NHS organisations list (e.g. a retired organisation).

Region() on the submission row itself is resolved from this same
now-enriched organisation data — not from whatever was in
nhs_organisations before this call started — so a submission whose
organisation is newly discovered in this same fetch still gets its correct
Region() immediately, rather than only on some later fetch.

unit_name is sourced from submission_name_map (the same live
/projects/{id}/submissions response's real submissionName per
submissionId), falling back to anonSubmissionCode only if a submission is
genuinely absent from that map. unit_code stays as anonSubmissionCode
throughout — the two are deliberately different fields now, rather than
both holding the same anonymised value.

Unmapped organisations. A submission whose organisation_id has no entry in
org_id_map (Functional Spec Section 7.4) is not treated as an error at this
layer: it's added to the population table exactly as normal, just with no
organisation link. merge_timeseries_population reports this back to its
caller (fetch.py) as a boolean, so a single warning can be surfaced once
per fetch run rather than per submission.
"""

from datetime import datetime

from core.acquisition.toolkit_nhs.api_client import get_organisations as get_nhs_organisations
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
        # Current calendar year — Indicators data has no year of its own
        # (periods only), so "now" is the intended stand-in, not a guess.
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
                # Resolved via the live org_id_map but not present in this
                # year's NHS organisations list (e.g. a retired
                # organisation) — fall back to the Indicators response's
                # own values, same as before this enrichment step existed.
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
