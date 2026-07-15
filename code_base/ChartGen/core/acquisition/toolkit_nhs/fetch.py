"""
fetch.py
Orchestrates the full data acquisition process for all live (non-deleted)
rows in WorkfileState's manifest table.
"""

import os
from core.acquisition.template.url_parser import parse_url
from .api_client import get_tier_info, get_chart_data
from .transformers import transform
from .cache_writer import save_chart


def fetch_all(token: str, *, workfile_state, on_progress=None) -> list[dict]:
    """
    Fetch, transform, and cache data for every non-deleted manifest row with
    a URL — a full refresh. Updates each row's fetch-populated columns
    (chart_title, project_id, service_id, year, shape_type, data_updated_at)
    as it goes.

    Returns a list of result dicts, one per row:
    {
        "hex_id": str, "label": str, "status": "ok" | "error",
        "message": str, "filepath": str | None, "shape_type": str | None,
    }
    """
    rows = [r for r in workfile_state.manifest_rows
            if str(r.get("deleted", "0")) != "1" and r.get("url", "").strip()]
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
