"""
workfile_file.py
Owns the .cgw ZIP format and WorkfileState — the in-memory representation of a workfile.
"""

import io
import json
import zipfile
import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.shared.infrastructure.constants import coerce_row

CHARTGEN_VERSION = "0.1-prototype"

# units.csv column schema. Moved here from constants_temp.py during the
# restructure (Restructure_Plan.md Open Item 2 audit) — this is workfile
# domain schema, used only by this module, not a generic constant.
UNITS_FIELDNAMES = [
    "unit_id",
    "unit_code",
    "unit_name",
    "submission_year",
    "project_id",
    "project_name",
    "organisation_id",
    "organisation_name",
    "submission_service_count",
    "response_count",
    "submission_level",
    "service_item_ids",
    "service_item_names",
    "service_response_counts",
    "Region()",
]


@dataclass
class WorkfileState:
    """
    In-memory representation of everything inside a .cgw file.
    Loaded from ZIP at open; serialised back to ZIP on save.
    """
    # File identity
    workfile_path: str = ""             # absolute path to .cgw on disk
    workfile_name: str = ""             # used as the file name (without .cgw)

    # workfile_config/
    settings: dict = field(default_factory=dict)
    urls: list = field(default_factory=list)          # list of {url, label}
    units: list = field(default_factory=list)         # list of dicts
    running_order_rows: list = field(default_factory=list)  # list of dicts (CSV rows)

    # data_cache/
    manifest: dict = field(default_factory=dict)      # keyed by tier_group_option key
    cache: dict = field(default_factory=dict)         # keyed by filename -> json string

    # template/
    template_pptx_bytes: Optional[bytes] = None       # reference copy bytes

    # workfile_info.json
    last_saved_by: str = ""
    last_saved_at: str = ""
    locked_by: str = ""
    locked_at: str = ""

    # Session state — not persisted
    dirty: bool = False
    read_only: bool = False   # True for sessions opened via "Open Read-Only"; never holds the lock


# ---------------------------------------------------------------------------
# Internal CSV helpers
# ---------------------------------------------------------------------------

def _csv_to_rows(text: str) -> list:
    """Parse CSV text into a list of dicts."""
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _rows_to_csv(rows: list, fieldnames: list = None) -> str:
    """Serialise a list of dicts to CSV text."""
    if not rows and not fieldnames:
        return ""
    out = io.StringIO()
    fn = fieldnames or list(rows[0].keys())
    writer = csv.DictWriter(out, fieldnames=fn)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def _key_value_csv_to_dict(text: str) -> dict:
    """Parse a key/value CSV (key,value header) into a dict."""
    reader = csv.DictReader(io.StringIO(text))
    return {row["key"]: row["value"].strip() for row in reader}


def _dict_to_key_value_csv(d: dict) -> str:
    """Serialise a dict to key/value CSV."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["key", "value"])
    writer.writeheader()
    for k, v in d.items():
        writer.writerow({"key": k, "value": v})
    return out.getvalue()


def _url_csv_to_list(text: str) -> list:
    """Parse urls.csv (url,label, no header) into list of dicts."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 1)
        rows.append({"url": parts[0].strip(), "label": parts[1].strip() if len(parts) > 1 else ""})
    return rows


def _url_list_to_csv(urls: list) -> str:
    """Serialise url list back to urls.csv format (no header)."""
    return "\n".join(f"{u['url']},{u.get('label','')}" for u in urls)


# ---------------------------------------------------------------------------
# Read workfile_info.json from ZIP without full extraction
# ---------------------------------------------------------------------------

def read_workfile_info(workfile_path: str) -> dict:
    """
    Read workfile_info.json from a .cgw without loading the full archive.
    Returns empty dict if file does not exist or cannot be read.
    """
    try:
        with zipfile.ZipFile(workfile_path, "r") as zf:
            if "workfile_info.json" in zf.namelist():
                return json.loads(zf.read("workfile_info.json").decode("utf-8"))
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Open
# ---------------------------------------------------------------------------

def open_workfile(workfile_path: str) -> WorkfileState:
    """
    Load a .cgw into a WorkfileState.
    Does NOT write lock fields — caller writes lock after successful login.
    """
    state = WorkfileState(workfile_path=workfile_path)

    with zipfile.ZipFile(workfile_path, "r") as zf:
        names = zf.namelist()

        def _read(name):
            return zf.read(name).decode("utf-8") if name in names else ""

        def _read_bytes(name):
            return zf.read(name) if name in names else None

        # workfile_config/
        state.settings         = _key_value_csv_to_dict(_read("workfile_config/settings.csv"))
        state.urls             = _url_csv_to_list(_read("workfile_config/urls.csv"))
        state.units            = _csv_to_rows(_read("workfile_config/units.csv"))
        state.running_order_rows = _csv_to_rows(_read("workfile_config/running_order.csv"))
        for _row in state.running_order_rows:
            _row.setdefault("enabled", "1")
            coerce_row(_row)

        # data_cache/
        if "data_cache/manifest.json" in names:
            state.manifest = json.loads(zf.read("data_cache/manifest.json").decode("utf-8"))
        for name in names:
            if name.startswith("data_cache/") and name.endswith(".json") and name != "data_cache/manifest.json":
                fname = name.split("/")[-1]
                state.cache[fname] = zf.read(name).decode("utf-8")

        # template/
        for name in names:
            if name.startswith("template/") and name.endswith(".pptx"):
                state.template_pptx_bytes = _read_bytes(name)
                break

        # workfile_info.json
        if "workfile_info.json" in names:
            info = json.loads(zf.read("workfile_info.json").decode("utf-8"))
            state.workfile_name  = info.get("workfile_name", "")
            state.last_saved_by  = info.get("last_saved_by", "")
            state.last_saved_at  = info.get("last_saved_at", "")
            state.locked_by      = info.get("locked_by", "")
            state.locked_at      = info.get("locked_at", "")

    state.dirty = False
    return state


def write_lock(workfile_path: str, username: str):
    """
    Write locked_by / locked_at into workfile_info.json inside the .cgw.
    Called after successful login.
    """
    _update_workfile_info(workfile_path, {
        "locked_by": username,
        "locked_at": datetime.now(timezone.utc).isoformat(),
    })


def clear_lock(workfile_path: str):
    """
    Clear locked_by / locked_at from workfile_info.json inside the .cgw.
    Called on any close route.
    """
    _update_workfile_info(workfile_path, {
        "locked_by": "",
        "locked_at": "",
    })


def _update_workfile_info(workfile_path: str, updates: dict):
    """Read workfile_info.json from .cgw, apply updates, and write back."""
    try:
        info = read_workfile_info(workfile_path)
        info.update(updates)
        _rewrite_single_file(workfile_path, "workfile_info.json",
                             json.dumps(info, indent=2).encode("utf-8"),
                             compress_type=zipfile.ZIP_STORED)
    except Exception:
        pass


def _rewrite_single_file(workfile_path: str, arcname: str, data: bytes, compress_type=zipfile.ZIP_DEFLATED):
    """Replace a single file inside a ZIP by rewriting the full archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(workfile_path, "r") as zin:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == arcname:
                    zout.writestr(zipfile.ZipInfo(arcname), data)
                    # set compression on the ZipInfo
                    zout.NameToInfo[arcname].compress_type = compress_type
                else:
                    zout.writestr(item, zin.read(item.filename))
            if arcname not in [i.filename for i in zin.infolist()]:
                info = zipfile.ZipInfo(arcname)
                info.compress_type = compress_type
                zout.writestr(info, data)
    with open(workfile_path, "wb") as f:
        f.write(buf.getvalue())


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_workfile(state: WorkfileState, username: str, target_path: str = None):
    """
    Serialise WorkfileState back to the .cgw ZIP, updating last_saved_by/at but not lock fields.
    target_path overrides state.workfile_path (used by Save As).
    """
    now = datetime.now(timezone.utc).isoformat()
    state.last_saved_by = username
    state.last_saved_at = now

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        def _write(arcname, text):
            zf.writestr(arcname, text.encode("utf-8"))

        # workfile_config/
        _write("workfile_config/settings.csv",      _dict_to_key_value_csv(state.settings))
        _write("workfile_config/urls.csv",           _url_list_to_csv(state.urls))
        _write("workfile_config/units.csv",
               _rows_to_csv(state.units, UNITS_FIELDNAMES) if state.units else "")

        # running_order — derive fieldnames from rows if present
        if state.running_order_rows:
            from core.output_generation.definition.running_order import COLUMNS
            _write("workfile_config/running_order.csv",
                   _rows_to_csv(state.running_order_rows, COLUMNS))
        else:
            _write("workfile_config/running_order.csv", "")

        # data_cache/
        _write("data_cache/manifest.json", json.dumps(state.manifest, indent=2))
        for fname, json_str in state.cache.items():
            zf.writestr(f"data_cache/{fname}", json_str.encode("utf-8"))

        # template/
        if state.template_pptx_bytes:
            workfile_name = state.workfile_name or "template"
            zf.writestr(f"template/{workfile_name}.pptx", state.template_pptx_bytes)

        # workfile_info.json — uncompressed
        info = {
            "workfile_name":     state.workfile_name,
            "last_saved_by":     state.last_saved_by,
            "last_saved_at":     state.last_saved_at,
            "chartgen_version":  CHARTGEN_VERSION,
            "locked_by":         state.locked_by,
            "locked_at":         state.locked_at,
        }
        zi = zipfile.ZipInfo("workfile_info.json")
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, json.dumps(info, indent=2).encode("utf-8"))

    save_path = target_path or state.workfile_path
    with open(save_path, "wb") as f:
        f.write(buf.getvalue())

    state.workfile_path = save_path
    state.dirty = False


# ---------------------------------------------------------------------------
# New
# ---------------------------------------------------------------------------

def new_workfile(workfile_path: str, workfile_name: str) -> WorkfileState:
    """
    Create a blank WorkfileState and write an empty .cgw to disk.
    Caller populates settings / units / etc. before first save.
    """
    state = WorkfileState(
        workfile_path=workfile_path,
        workfile_name=workfile_name,
        dirty=True,
    )
    # Write a minimal .cgw immediately so the file exists on disk
    _write_empty_cgw(workfile_path, workfile_name)
    return state


def _write_empty_cgw(workfile_path: str, workfile_name: str):
    os.makedirs(os.path.dirname(workfile_path), exist_ok=True) if os.path.dirname(workfile_path) else None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in [
            "workfile_config/settings.csv",
            "workfile_config/urls.csv",
            "workfile_config/units.csv",
            "workfile_config/running_order.csv",
        ]:
            zf.writestr(name, b"")
        # empty manifest
        zf.writestr("data_cache/manifest.json", json.dumps({}).encode("utf-8"))
        # workfile_info
        info = {
            "workfile_name":    workfile_name,
            "last_saved_by":    "",
            "last_saved_at":    "",
            "chartgen_version": CHARTGEN_VERSION,
            "locked_by":        "",
            "locked_at":        "",
        }
        zi = zipfile.ZipInfo("workfile_info.json")
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, json.dumps(info, indent=2).encode("utf-8"))
    with open(workfile_path, "wb") as f:
        f.write(buf.getvalue())


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------

def close_workfile(state: WorkfileState):
    """
    Clear lock fields in the .cgw and discard the WorkfileState.
    Skipped for read-only sessions, which never claim the lock.
    """
    if state.read_only:
        return
    if state.workfile_path and os.path.exists(state.workfile_path):
        clear_lock(state.workfile_path)
