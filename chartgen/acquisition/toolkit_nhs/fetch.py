"""
fetch.py
Orchestrates the full data acquisition process for all live (non-deleted)
rows in WorkfileState's manifest table.
"""

import os
from dataclasses import replace

from chartgen.acquisition.template.url_parser import parse_url
from .api_client import get_tier_info, get_chart_data
from .table_naming import submissions_table_name
from .population_tables import ensure_population_tables, ORGANISATIONS_TABLE
from .transformers import transform, CYCLE_PROCS
from chartgen.shared.infrastructure.cache_writer import save_chart
from chartgen.shared.infrastructure.soft_parents import parse_soft_parents


def _optional_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _fetch_cycled_unit_responses(
    report_id, group, year, service_item_id, option, token,
    workfile_state, project_id,
):
    """
    For CYCLE_PROCS (currently only sp_a_generic_radar_to_dual_bar): this
    procedure's own aggregate call never returns per-submission data —
    tableData is always empty. The only way to get a given organisation's
    values is to pass its organisation_id back into get_chart_data, which
    then populates response2 per segment for that organisation alone. This
    cycles that call once per distinct organisation_id in the project's
    submissions table.

    Known limitation, not yet resolved: get_chart_data is driven by
    organisation_id, not submission_id. Where an organisation has more than
    one submission, every submission belonging to that organisation is
    assigned the same values here — there is currently no API-level way to
    tell its submissions apart. Needs verifying against a real
    multi-submission organisation during testing.

    Returns a list of (unit_code, unit_id, values) tuples, one per
    submission, suitable for transform()'s per_unit_responses parameter.
    """
    sub_table_name = submissions_table_name(year, project_id)
    submission_rows = workfile_state.tables.get(sub_table_name, [])

    by_org = {}
    for row in submission_rows:
        org_ids = parse_soft_parents(row.get("soft_parents", "")).get(ORGANISATIONS_TABLE, [])
        if not org_ids:
            continue
        by_org.setdefault(org_ids[0], []).append(row)

    per_unit_responses = []
    for org_id, rows in by_org.items():
        try:
            org_json = get_chart_data(
                report_id=report_id,
                group=group,
                year=year,
                service_item_id=service_item_id,
                option=option,
                token=token,
                organisation_id=int(org_id),
            )
        except Exception:
            # Skip this organisation's contribution rather than failing the
            # whole chart fetch — matches fetch_all's own per-row isolation.
            continue

        org_year_data = org_json.get("data", {}).get("yearData", {}).get(year, [])
        values = [_optional_float(item.get("response2")) for item in org_year_data]
        if not any(v is not None for v in values):
            continue

        for row in rows:
            per_unit_responses.append((row["unit_code"], str(row["unit_id"]), values))

    return per_unit_responses


def fetch_all(token: str, *, workfile_state, on_progress=None) -> list[dict]:
    """
    Fetch, transform, and cache data for every non-deleted manifest row with
    a URL whose database is "nhs" — a full refresh of this toolkit's own
    rows only. Rows for other databases (e.g. "indicators") are left alone;
    chartgen.acquisition.fetch_dispatch is what combines every toolkit's
    fetch_all into a single Fetch action. Updates each row's
    fetch-populated columns (chart_title, project_id, service_id, year,
    shape_type, data_updated_at) as it goes.

    Returns a list of result dicts, one per row:
    {
        "hex_id": str, "label": str, "status": "ok" | "error",
        "message": str, "filepath": str | None, "shape_type": str | None,
    }
    """
    rows = [r for r in workfile_state.manifest_rows
            if str(r.get("deleted", "0")) != "1" and r.get("url", "").strip()
            and str(r.get("database", "nhs")).strip() == "nhs"]
    results = []
    total = len(rows)

    for i, row in enumerate(rows):
        label = _display_label(row)

        if on_progress:
            on_progress(i + 1, total, label)

        try:
            parsed = parse_url(row["url"])
            tier_id = parsed["tier_id"]
            group   = parsed["group"]
            option  = parsed["option"]

            # API call 1: tier metadata
            tier_info  = get_tier_info(tier_id, token)
            data_block = tier_info["data"]
            # Use most recent visible year
            report_years = data_block["reportYears"]
            visible = [y for y in report_years if y.get("isVisible") == "Y"]
            latest = max(visible or report_years, key=lambda y: y["reportYear"])
            report_id      = str(latest["reportId"])
            year           = str(latest["reportYear"])
            service_item_id = str(data_block.get("serviceItemId") or "0")

            # This chart's year/project_id are now known. Before pulling its
            # own data, make sure its population tables exist — the first
            # chart seen for a given project/year combination is what
            # triggers building the submissions + nhs_organisations tables;
            # every subsequent chart for that same combination finds them
            # already there and does nothing extra.
            ensure_population_tables(workfile_state, year, parsed["project_id"], token)

            # API call 2: chart data
            raw_json = get_chart_data(
                report_id=report_id,
                group=group,
                year=year,
                service_item_id=service_item_id,
                option=option,
                token=token,
            )

            # CYCLE_PROCS: the aggregate call alone doesn't carry real
            # per-unit data for these (see _fetch_cycled_unit_responses).
            # Cycle per organisation before transforming so the shape gets
            # real units instead of the single synthetic SAMPLE_AVG fallback.
            proc = raw_json.get("data", {}).get("storedProcedure")
            per_unit_responses = None
            if proc in CYCLE_PROCS:
                per_unit_responses = _fetch_cycled_unit_responses(
                    report_id=report_id,
                    group=group,
                    year=year,
                    service_item_id=service_item_id,
                    option=option,
                    token=token,
                    workfile_state=workfile_state,
                    project_id=parsed["project_id"],
                )

            # Transform to canonical shape
            shape = transform(raw_json, year, option, per_unit_responses=per_unit_responses)
            # Stamp which population table this data's units belong to, and
            # record the source URL in the shape's own metadata (recorded
            # once, at the point of pulling the data — see chart construction,
            # Data Shapes). All data is submissions data today, so
            # population_table is always the submissions table for the
            # chart's own project/year — not necessarily the workfile's
            # current master table.
            shape = replace(
                shape,
                population_table=submissions_table_name(year, parsed["project_id"]),
                metadata={**shape.metadata, "source_url": row["url"]},
            )
            shape_type = type(shape).__name__
            chart_title = str(getattr(shape, "title", "") or "").strip()

            # Save normalised shape to cache and update the manifest row
            filepath = save_chart(
                row, shape, shape_type,
                chart_title=chart_title,
                project_id=parsed["project_id"],
                service_id=service_item_id,
                year=year,
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

    return results


def _display_label(row: dict) -> str:
    """Best available human label for a manifest row in progress/result output."""
    title = str(row.get("chart_title", "")).strip()
    if title and title != "...":
        return title
    return f"{row.get('chart_ref') or row.get('hex_id', '')}: {row.get('url', '')[:60]}"
