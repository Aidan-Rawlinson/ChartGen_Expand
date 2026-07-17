"""
fetch.py
Orchestrates data acquisition for every non-deleted manifest row whose
database is "indicators". Mirrors toolkit_nhs/fetch.py's shape, with two
deliberate differences: the population table is merged on every row, not
built once and then skipped (see population_tables.py for why), and one
project-level API call (/projects/{id}/submissions) is fetched once per
project_id per run, not once per row — the source VBA re-fetches its
date-only equivalent every row, but it's genuinely project-level data, so
caching it here avoids a same-value round trip per chart. That same call
now also supplies the live organisation-id mapping and real submission
names used by population_tables.py — see get_project_submissions_data.

Accumulates a single any_unmapped_org flag across every row in the run
(population_tables.merge_timeseries_population reports one per call) and,
if set, appends one synthetic "warning"-status entry to the returned
results — see population_tables.py for what triggers it.
"""

import os
from dataclasses import replace

from .url_parser import parse_url
from .api_client import get_report_details, get_report_data, get_project_submissions_data
from .table_naming import submissions_timeseries_table_name
from .population_tables import merge_timeseries_population
from .transformers import transform
from core.shared.infrastructure.cache_writer import save_chart


def fetch_all(token: str, *, workfile_state, on_progress=None) -> list[dict]:
    """
    Fetch, transform, and cache data for every non-deleted manifest row with
    a URL whose database is "indicators". Same return shape as
    toolkit_nhs.fetch.fetch_all — see core.acquisition.fetch_dispatch for
    where the two are combined into the Imports tab's single Fetch action.
    """
    rows = [r for r in workfile_state.manifest_rows
            if str(r.get("deleted", "0")) != "1" and r.get("url", "").strip()
            and str(r.get("database", "nhs")).strip() == "indicators"]
    results = []
    total = len(rows)
    project_data_cache = {}  # project_id -> full /projects/{id}/submissions response, one API call per project per fetch_all run
    any_unmapped_org = False  # set if any submission's organisation_id had no live org mapping entry — see population_tables.py

    for i, row in enumerate(rows):
        label = _display_label(row)

        if on_progress:
            on_progress(i + 1, total, label)

        try:
            parsed = parse_url(row["url"])
            project_id = parsed["project_id"]
            report_id = parsed["report_id"]
            tier_id = parsed["tier_id"]

            report_details = get_report_details(report_id, token)
            report_data = get_report_data(report_id, token)

            if project_id not in project_data_cache:
                project_data_cache[project_id] = get_project_submissions_data(project_id, token)
            project_data = project_data_cache[project_id]
            project_dates = project_data["projectDates"]
            user_organisations = project_data.get("userOrganisations", [])

            # Live org-id mapping and real submission names — sourced from
            # this same project-level response, not a static file. See
            # population_tables.py for how each is used.
            org_id_map = {
                str(o["organisationId"]): (
                    str(o["externalOrganisationId"]) if o.get("externalOrganisationId") is not None else None
                )
                for o in user_organisations
            }
            submission_name_map = {
                str(sub["submissionId"]): sub.get("submissionName", "")
                for o in user_organisations
                for sub in o.get("submissionList", [])
            }

            # Population table: merge on every row, not build-once — see
            # population_tables.py. A single report response can itself
            # introduce submissions the table doesn't have yet.
            _, had_unmapped = merge_timeseries_population(
                workfile_state, project_id, report_data,
                token=token, org_id_map=org_id_map, submission_name_map=submission_name_map,
            )
            any_unmapped_org = any_unmapped_org or had_unmapped

            shape = transform(report_details, report_data, project_dates)
            shape = replace(shape, population_table=submissions_timeseries_table_name(project_id))
            shape_type = type(shape).__name__
            chart_title = str(getattr(shape, "title", "") or "").strip()

            filepath = save_chart(
                row, shape, shape_type,
                chart_title=chart_title,
                project_id=project_id,
                service_id=str(tier_id) if tier_id is not None else "",
                year="",  # not applicable — Indicators data is periods, not years
                workfile_state=workfile_state,
            )

            results.append({
                "hex_id":     row["hex_id"],
                "label":      _display_label(row),
                "status":     "ok",
                "message":    f"{shape_type} → {os.path.basename(filepath)}",
                "filepath":   filepath,
                "shape_type": shape_type,
            })

        except Exception as e:
            results.append({
                "hex_id":     row.get("hex_id", ""),
                "label":      label,
                "status":     "error",
                "message":    str(e),
                "filepath":   None,
                "shape_type": None,
            })

    if any_unmapped_org:
        results.append({
            "hex_id":     "",
            "label":      "Organisation mapping",
            "status":     "warning",
            "message":    "One or more submissions have no organisation match in this "
                          "project's own organisation data — those submissions were "
                          "added with no organisation link.",
            "filepath":   None,
            "shape_type": None,
        })

    return results


def _display_label(row: dict) -> str:
    """Best available human label for a manifest row in progress/result output."""
    title = str(row.get("chart_title", "")).strip()
    if title and title != "...":
        return title
    return f"{row.get('chart_ref') or row.get('hex_id', '')}: {row.get('url', '')[:60]}"
