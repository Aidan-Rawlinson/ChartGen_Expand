"""
fetch.py
Orchestrates the full data acquisition process for all live (non-deleted)
rows in WorkfileState's manifest table.
"""

import os
from dataclasses import replace

from core.acquisition.template.url_parser import parse_url
from .api_client import get_tier_info, get_chart_data
from .table_naming import submissions_table_name
from .population_tables import ensure_population_tables
from .transformers import transform
from core.shared.infrastructure.cache_writer import save_chart


def fetch_all(token: str, *, workfile_state, on_progress=None) -> list[dict]:
    """
    Fetch, transform, and cache data for every non-deleted manifest row with
    a URL whose database is "nhs" — a full refresh of this toolkit's own
    rows only. Rows for other databases (e.g. "indicators") are left alone;
    core.acquisition.fetch_dispatch is what combines every toolkit's
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

            # Transform to canonical shape
            shape = transform(raw_json, year)
            # Stamp which population table this data's units belong to. All
            # data is submissions data today, so this is always the
            # submissions table for the chart's own project/year — not
            # necessarily the workfile's current master table.
            shape = replace(shape, population_table=submissions_table_name(year, parsed["project_id"]))
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
