"""
cache_writer.py
Serialises canonical data shapes into WorkfileState's cache, keyed by the
manifest row's hex_id, and updates that row's fetch-populated columns
(chart_title, project_id, service_id, year, shape_type, data_updated_at).
"""

import json
import dataclasses
from datetime import datetime, timezone


def _serialise(obj):
    """Recursively serialise dataclasses to dicts for JSON output."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialise(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialise(v) for v in obj]
    return obj


def save_chart(manifest_row: dict, shape, shape_type: str, *,
               chart_title: str = "", project_id="", service_id="", year="",
               workfile_state) -> str:
    """
    Serialise a canonical data shape into WorkfileState.cache as
    {hex_id}.json and update the given manifest row's fetch-populated
    columns. Returns the cache filename.
    """
    hex_id = manifest_row["hex_id"]
    filename = f"{hex_id}.json"
    payload = {
        "shape_type": shape_type,
        "data": _serialise(shape),
    }
    workfile_state.cache[filename] = json.dumps(payload, indent=2)

    if chart_title:
        manifest_row["chart_title"] = chart_title
    manifest_row["project_id"]      = str(project_id)
    manifest_row["service_id"]      = str(service_id)
    manifest_row["year"]            = str(year)
    manifest_row["shape_type"]      = shape_type
    manifest_row["data_updated_at"] = datetime.now(timezone.utc).isoformat()

    workfile_state.dirty = True
    return filename
