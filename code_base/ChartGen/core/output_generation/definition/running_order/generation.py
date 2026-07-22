"""
generation.py
Running Order generation from a template read result: builds the full row
list (create_ppt header, per-placeholder content rows, save_ppt/save_pdf
footer, and batch open/close Excel pairs).
"""

import os

from core.output_generation.execution.charts.chart_type_map import get_chart_types_by_shape


def default_chart_type_ref_for_shape(shape_type: str, chart_types_by_shape: dict) -> str:
    """
    First valid chart_type_ref for shape_type, per chart_type_map.csv's own
    row order. Returns "" if shape_type isn't resolvable against the map
    (e.g. still the pre-fetch placeholder).
    """
    return chart_types_by_shape.get(shape_type, [""])[0]


def backfill_default_chart_types(rows: list[dict], manifest: dict) -> int:
    """
    Fill in chart_type_ref for any insert_chart row that's still blank, now
    that shape_type is known from a fetch. Never touches a row whose
    chart_type_ref is already set — whether from a prior backfill or a
    manual edit. Called once, at the end of Fetch (see import_flow.py);
    generation time is too early, since shape_type is never known until a
    fetch has happened.

    Returns the number of rows backfilled.
    """
    chart_types_by_shape = get_chart_types_by_shape()
    backfilled = 0
    for row in rows:
        if row.get("function") != "insert_chart" or row.get("chart_type_ref", ""):
            continue
        cache_file = row.get("cache_file", "")
        shape_type = manifest.get(cache_file, {}).get("shape_type", "")
        default_ref = default_chart_type_ref_for_shape(shape_type, chart_types_by_shape)
        if default_ref:
            row["chart_type_ref"] = default_ref
            backfilled += 1
    return backfilled


def generate_from_template(
    template_result,          # TemplateReadResult from the Template Reader module
    manifest: dict,           # filename -> {url, shape_type, ...} manifest table rows
) -> list[dict]:
    """
    Build a list of Running Order row dicts from a TemplateReadResult.

    For each placeholder, based on content_type:
      "chart"   → insert_chart row (chart_type_ref blank; backfilled once
                  Fetch has run — see backfill_default_chart_types below)
      "picture" → insert_picture row (image_path populated from the placeholder's yellow box)
      "excel"   → insert_from_excel row (excel_path, export_range, driver_range populated)
      ""        → empty_placeholder row

    For each unique Excel workbook referenced, a paired open_excel (scope=batch_open)
    and close_excel (scope=batch_close) row is added — one pair per workbook.

    Returns the full list including create_ppt header and save_ppt/save_pdf footer.
    """
    rows = []
    row_id = 1

    def _blank_row(func, note="", scope="normal"):
        return {
            "row_id": row_id, "enabled": 1, "scope": scope, "function": func,
            "slide_index": "", "chart_type_ref": "",
            "cache_file": "", "populations": "", "start_period": "", "end_period": "",
            "metric_periods": "",
            "image_path": "", "excel_path": "", "export_range": "", "driver_range": "",
            "left_emu": "", "top_emu": "", "width_emu": "", "height_emu": "",
            "notes": note,
        }

    # --- Collect unique Excel workbooks to generate batch open/close pairs ---
    excel_paths_seen = []   # ordered, deduped
    for ph in template_result.placeholders:
        if ph.content_type == "excel" and ph.excel_path:
            if ph.excel_path not in excel_paths_seen:
                excel_paths_seen.append(ph.excel_path)

    # batch_open rows — absolute top, before all per-report rows
    for ep in excel_paths_seen:
        rows.append({**_blank_row("open_excel",
                                  f"Open workbook for batch: {os.path.basename(ep)}",
                                  scope="batch_open"),
                     "excel_path": ep})
        row_id += 1

    # --- Header rows (per-report) ---
    rows.append(_blank_row("create_ppt", "Open template and save working copy"))
    row_id += 1

    rows.append({**_blank_row("set_default_populations",
                              "Default populations for all charts — override per row in the populations column"),
                 "populations": "All^Selected"})
    row_id += 1

    rows.append(_blank_row("update_text", "Replace flag tokens with reporting unit values"))
    row_id += 1

    # --- Build URL → cache filename lookup ---
    url_to_cache = _build_url_to_cache_map(manifest)

    # --- One row per placeholder ---
    for ph in sorted(template_result.placeholders, key=lambda p: (p.slide_index, p.name)):
        ct = ph.content_type

        base = {
            "row_id": row_id, "enabled": 1, "scope": "normal",
            "slide_index": ph.slide_index, "chart_type_ref": "", "cache_file": "", "populations": "",
            "start_period": "", "end_period": "", "metric_periods": "",
            "image_path": "", "excel_path": "", "export_range": "", "driver_range": "",
            "left_emu": ph.left, "top_emu": ph.top,
            "width_emu": ph.width, "height_emu": ph.height,
            "notes": "",
        }

        if ct == "chart":
            cache_file = url_to_cache.get(_normalise_url(ph.url), "")
            rows.append({**base,
                "function": "insert_chart",
                "cache_file": cache_file,
                "notes": ph.label or "",
            })

        elif ct == "picture":
            rows.append({**base,
                "function": "insert_picture",
                "image_path": ph.image_path,
                "notes": f"Picture: {os.path.basename(ph.image_path)}",
            })

        elif ct == "excel":
            rows.append({**base,
                "function": "insert_from_excel",
                "excel_path":   ph.excel_path,
                "export_range": ph.excel_export_range,
                "driver_range": ph.excel_driver_range,
                "notes": f"Excel export: {ph.excel_export_range} from {os.path.basename(ph.excel_path)}",
            })

        else:
            rows.append({**base, "function": "empty_placeholder"})

        row_id += 1

    # --- Footer rows (per-report) ---
    rows.append(_blank_row("save_ppt", "Save output as .pptx"))
    row_id += 1

    rows.append({**_blank_row("save_pdf", "Save output as .pdf (requires PowerPoint installed)"),
                 "enabled": 0})
    row_id += 1

    # batch_close rows — absolute bottom, after all per-report rows
    for ep in excel_paths_seen:
        rows.append({**_blank_row("close_excel",
                                  f"Close workbook after batch: {os.path.basename(ep)}",
                                  scope="batch_close"),
                     "excel_path": ep})
        row_id += 1

    return rows


def _normalise_url(url: str) -> str:
    """Strip trailing slashes and whitespace for comparison."""
    return url.strip().rstrip("/")


def _build_url_to_cache_map(manifest: dict) -> dict:
    """Build url -> cache_filename map from the manifest."""
    mapping = {}
    for filename, entry in manifest.items():
        url = entry.get("url", "")
        if url:
            mapping[_normalise_url(url)] = filename
    return mapping
