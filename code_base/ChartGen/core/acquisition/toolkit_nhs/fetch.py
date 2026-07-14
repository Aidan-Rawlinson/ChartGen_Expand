"""
fetch.py
Orchestrates the full data acquisition process for all URLs in WorkfileState.
"""

import os
from core.acquisition.template.url_parser import parse_url
from .api_client import get_tier_info, get_chart_data
from .transformers import transform
from .cache_writer import save_chart


def fetch_all(token: str, *, workfile_state, on_progress=None) -> list[dict]:
    """
    Fetch, transform, and cache data for all URLs in WorkfileState.urls.

    Returns a list of result dicts, one per URL:
    {
        "tier_id": int, "label": str, "status": "ok" | "error",
        "message": str, "filepath": str | None, "shape_type": str | None,
    }
    """
    urls = [parse_url(u["url"], u.get("label", "")) for u in workfile_state.urls if u.get("url")]
    results = []
    total = len(urls)

    for i, parsed in enumerate(urls):
        tier_id = parsed["tier_id"]
        group   = parsed["group"]
        option  = parsed["option"]
        label   = parsed["label"]

        if on_progress:
            on_progress(i + 1, total, label)

        try:
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

            # Save normalised shape to cache
            filepath = save_chart(tier_id, group, option, label, shape, shape_type, url=parsed["url"], workfile_state=workfile_state)

            results.append({
                "tier_id":    tier_id,
                "label":      label,
                "status":     "ok",
                "message":    f"{shape_type} → {os.path.basename(filepath)}",
                "filepath":   filepath,
                "shape_type": shape_type,
            })

        except Exception as e:
            results.append({
                "tier_id":    tier_id,
                "label":      label,
                "status":     "error",
                "message":    str(e),
                "filepath":   None,
                "shape_type": None,
            })

    return results
