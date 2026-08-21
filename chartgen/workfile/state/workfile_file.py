"""
workfile_file.py
Owns the .cgw ZIP format and WorkfileState — the in-memory representation of a workfile.
"""

import io
import json
import zipfile
import csv
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from chartgen.shared.infrastructure.constants import coerce_row
from chartgen.shared.infrastructure.version_compatibility import (
    get_file_version_written, get_software_id,
)

# Population-level tables (nhs_organisations, submissions_{year}_{project_id},
# and any future table) have no single fixed column schema here — each is
# written using its own rows' keys (see _rows_to_csv's fallback). Every such
# table shares a common spine (unit_id, unit_code, unit_name, soft_parents,
# plus any number of Name() peer-group columns); the actual column list for
# a given table is owned by whichever module builds its rows — new_workfile.py
# for the tables built at New Workfile time.

# data_cache/manifest.csv column schema — the URL/chart table. One row per
# chart URL, keyed permanently by hex_id. Replaces the former
# workfile_config/urls.csv and data_cache/manifest.json (single source of
# truth; the manifest is the index to the data_cache it sits inside).
# Unfetched cells hold the PLACEHOLDER value rather than sitting empty.
MANIFEST_FIELDNAMES = [
    "chart_ref",        # display index, Chart_0001 style — renumbers across non-deleted rows
    "hex_id",           # 5-digit hexadecimal, stable internal key — never reused, never renumbered
    "url",
    "chart_title",      # populated at fetch
    "database",         # "nhs" or "indicators" — resolved at URL entry by chartgen.acquisition.url_triage
    "project_id",       # populated at fetch
    "service_id",       # populated at fetch
    "year",             # populated at fetch
    "shape_type",       # populated at fetch
    "source",           # "Template" / "Direct Input"
    "deleted",          # 1/0 — deleted rows are hidden, skipped by fetch/export, hex_id stays reserved
    "added_at",         # ISO datetime the row was created
    "data_updated_at",  # ISO datetime data was last fetched
]

PLACEHOLDER = "..."

# workfile_config/custom_charts/custom_charts.csv column schema — the index
# of every custom Base Chart saved into this workfile. Source code itself
# lives alongside it, one file per row, at
# workfile_config/custom_charts/{shape_type}/{base_chart_name}.py — the same
# folder-per-shape convention the built-in Base Charts use (Architecture,
# base_charts/{shape}/). Mirrors the manifest/cache split: this file is the
# index, the .py files are the payload.
CUSTOM_CHART_FIELDNAMES = ["base_chart_name", "shape_type", "added_at", "notes"]

# workfile_config/custom_tables/custom_tables.csv column schema -- the
# index of every custom Base Table saved into this workfile (Decisions.md).
# Source code lives alongside it, one file per row, directly at
# workfile_config/custom_tables/{table_type_ref}.py -- no per-shape
# subfolder, unlike custom_charts, since a Base Table isn't scoped to any
# one canonical data shape (every one takes the same already-resolved
# grid). Mirrors the manifest/cache split the same way custom_charts does:
# this file is the index, the .py files are the payload.
CUSTOM_TABLE_FIELDNAMES = ["table_type_ref", "added_at", "notes"]

# workfile_config/text_stats.csv column schema — "stat tags": short,
# permanent tag ids (Decisions.md) standing in for one summary-stats value
# from one chart's own independently-authored cut of its cached data, for
# use in update_text (ordinary text frames and, as of this session, table
# cells too). Anchored on hex_id — the manifest's stable identity — rather
# than chart_ref, which renumbers whenever the manifest table changes.
# Genuinely new state, not derived from any Running Order row: a stat tag
# isn't tied to any specific insert_chart row.
TEXT_STATS_FIELDNAMES = [
    "tag",             # "T" + base-36 id, never reused — the literal [tag] template text
    "hex_id",          # manifest hex_id this tag's data comes from
    "populations",     # this tag's own single-token population (independent of any Running Order row)
    "start_period",    # TimeSeries only
    "end_period",      # TimeSeries only
    "metric_periods",  # TimeSeries only
    "reference_id",    # which Reference id (shapes/reference_ids.py) to read from that population
    "description",     # optional free text, user reference only, ignored at resolution
]

# workfile_config/output_tables/output_tables.csv column schema -- the
# index of every Output Table defined in this workfile (Decisions.md). This
# is the index only; the grid itself is one CSV per table_id, held
# alongside it at workfile_config/output_tables/{table_id}.csv, with no
# fixed column schema of its own (same convention as the population tables
# above) -- see chartgen.output_generation.execution.tables.grid_store for its
# internal layout (column widths / row heights / content cells).
OUTPUT_TABLE_FIELDNAMES = [
    "table_id",    # base-36 id, never reused -- also written, cosmetically only, into the grid's own corner cell
    "table_name",  # user-facing name -- user-typed for a manually-created table,
                   # auto-generated (Table_1, Table_2, ...) for a yellow-box one
                   # (Decisions.md: re-upload always creates a fresh set, never
                   # matched against an existing table by name)
    "rows",        # content grid row count (N), excluding the header row
    "columns",     # content grid column count (M), excluding the header column
]

# workfile_config/chart_store.csv column schema -- the Chart Store: a flat,
# unordered set of independently-authored chart-defs, for use as chart
# components inside Output Table cells (sparklines, grid layouts, etc) --
# independent of the Running Order, which is strictly a sequence of report
# content. Mirrors CHART_SANDBOX_FIELDS (the Charts sheet's own
# insert_chart round-trip field list) plus its own base-36 id (mirroring
# Stat Tags/Output Tables -- id_generation, settings["next_chart_store_id"])
# and an optional free-text description, the same convention text_stats.csv
# uses for its own rows.
CHART_STORE_FIELDNAMES = [
    "chart_store_id",  # "C" + base-36 id, never reused
    "base_chart_name",
    "cache_file",
    "populations",
    "start_period",
    "end_period",
    "metric_periods",
    "width_emu",
    "height_emu",
    "tweaks",
    "description",      # optional free text, user reference only
]


def generate_hex_id(existing_rows: list) -> str:
    """
    Generate a 5-digit uppercase hexadecimal id unique across all manifest
    rows, including deleted ones (deleted rows keep their hex_id reserved).
    """
    taken = {r.get("hex_id", "") for r in existing_rows}
    while True:
        hex_id = secrets.token_hex(3)[:5].upper()
        if hex_id not in taken:
            return hex_id


def new_manifest_row(url: str, source: str, existing_rows: list, database: str) -> dict:
    """
    Build a new manifest row for a URL, with a fresh hex_id and added_at,
    fetch-populated columns set to PLACEHOLDER. database is the caller's
    responsibility to resolve (see chartgen.acquisition.url_triage) — this
    function no longer defaults it, so a database can never be silently
    wrong just because a call site forgot to pass it. chart_ref is left
    blank — call renumber_chart_refs after appending.
    """
    return {
        "chart_ref":       "",
        "hex_id":          generate_hex_id(existing_rows),
        "url":             url.strip(),
        "chart_title":     PLACEHOLDER,
        "database":        database,
        "project_id":      PLACEHOLDER,
        "service_id":      PLACEHOLDER,
        "year":            PLACEHOLDER,
        "shape_type":      PLACEHOLDER,
        "source":          source,
        "deleted":         "0",
        "added_at":        datetime.now(timezone.utc).isoformat(),
        "data_updated_at": PLACEHOLDER,
    }


def renumber_chart_refs(manifest_rows: list):
    """
    Reassign chart_ref (Chart_0001 style) across non-deleted rows in table
    order. Deleted rows have chart_ref cleared. Call after any add, delete,
    or reimport.
    """
    n = 0
    for row in manifest_rows:
        if str(row.get("deleted", "0")) == "1":
            row["chart_ref"] = ""
        else:
            n += 1
            row["chart_ref"] = f"Chart_{n:04d}"


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
    tables: dict = field(default_factory=dict)         # {table_name: list[dict]} — every population-level table
    table_order: list = field(default_factory=list)    # display/priority order; table_order[0] is the master table
    running_order_rows: list = field(default_factory=list)  # list of dicts (CSV rows)

    # data_cache/
    manifest_rows: list = field(default_factory=list)  # the URL/chart table (manifest.csv), MANIFEST_FIELDNAMES
    cache: dict = field(default_factory=dict)         # keyed by filename ({hex_id}.json) -> json string

    # workfile_config/custom_charts/ — user- or AI-authored Base Charts,
    # saved into this workfile. custom_chart_rows mirrors manifest_rows
    # (the index); custom_chart_code mirrors cache (the payload, keyed by
    # base_chart_name rather than filename since that's this store's own
    # stable identity — see Decisions.md).
    custom_chart_rows: list = field(default_factory=list)  # CUSTOM_CHART_FIELDNAMES rows
    custom_chart_code: dict = field(default_factory=dict)  # {base_chart_name: source_text}

    # workfile_config/custom_tables/ -- user- or AI-authored Base Tables,
    # saved into this workfile. Mirrors custom_chart_rows/custom_chart_code
    # exactly, keyed by table_type_ref instead of base_chart_name, with no
    # shape_type dimension.
    custom_table_rows: list = field(default_factory=list)  # CUSTOM_TABLE_FIELDNAMES rows
    custom_table_code: dict = field(default_factory=dict)  # {table_type_ref: source_text}

    # workfile_config/text_stats.csv — "stat tags" (Decisions.md), TEXT_STATS_FIELDNAMES rows
    text_stats_rows: list = field(default_factory=list)

    # workfile_config/chart_store.csv -- Chart Store (Decisions.md):
    # independently-authored chart-defs, for use as chart components inside
    # Output Table cells. CHART_STORE_FIELDNAMES rows, flat and unordered --
    # no position/sequence concept, unlike running_order_rows.
    chart_store_rows: list = field(default_factory=list)

    # workfile_config/output_tables/ -- Output Tables (Decisions.md).
    # output_table_rows mirrors custom_chart_rows (the index, OUTPUT_TABLE_FIELDNAMES);
    # output_tables mirrors WorkfileState.tables (population tables) -- one
    # grid per table_id, no fixed column schema -- see grid_store.py.
    output_table_rows: list = field(default_factory=list)
    output_tables: dict = field(default_factory=dict)

    # template/
    template_pptx_bytes: Optional[bytes] = None       # reference copy bytes

    # workfile_info.json
    last_saved_by: str = ""
    last_saved_at: str = ""
    locked_by: str = ""
    locked_at: str = ""
    file_version_id: str = ""  # .cgw internal structure version - separate from the software id

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
        state.table_order      = [t for t in state.settings.get("table_order", "").split("|") if t]
        state.running_order_rows = _csv_to_rows(_read("workfile_config/running_order.csv"))
        for _row in state.running_order_rows:
            _row.setdefault("enabled", "1")
            coerce_row(_row)

        # workfile_config/tables/ — every population-level table, one CSV each
        for name in names:
            if name.startswith("workfile_config/tables/") and name.endswith(".csv"):
                table_name = name.split("/")[-1][:-4]
                state.tables[table_name] = _csv_to_rows(_read(name))

        # workfile_config/text_stats.csv — stat tags
        state.text_stats_rows = _csv_to_rows(_read("workfile_config/text_stats.csv"))

        # workfile_config/chart_store.csv -- Chart Store
        state.chart_store_rows = _csv_to_rows(_read("workfile_config/chart_store.csv"))

        # workfile_config/output_tables/ -- Output Tables: index plus one grid CSV per table_id
        state.output_table_rows = _csv_to_rows(
            _read("workfile_config/output_tables/output_tables.csv")
        )
        for name in names:
            if (name.startswith("workfile_config/output_tables/") and name.endswith(".csv")
                    and name != "workfile_config/output_tables/output_tables.csv"):
                table_id = name.split("/")[-1][:-4]
                state.output_tables[table_id] = _csv_to_rows(_read(name))

        # data_cache/
        state.manifest_rows = _csv_to_rows(_read("data_cache/manifest.csv"))
        for name in names:
            if name.startswith("data_cache/") and name.endswith(".json"):
                fname = name.split("/")[-1]
                state.cache[fname] = zf.read(name).decode("utf-8")

        # workfile_config/custom_charts/ — index plus one .py per row,
        # under workfile_config/custom_charts/{shape_type}/{base_chart_name}.py
        state.custom_chart_rows = _csv_to_rows(
            _read("workfile_config/custom_charts/custom_charts.csv")
        )
        for row in state.custom_chart_rows:
            ref = row.get("base_chart_name", "")
            shape = row.get("shape_type", "")
            py_path = f"workfile_config/custom_charts/{shape}/{ref}.py"
            if ref and py_path in names:
                state.custom_chart_code[ref] = _read(py_path)

        # workfile_config/custom_tables/ -- index plus one .py per row,
        # directly at workfile_config/custom_tables/{table_type_ref}.py
        state.custom_table_rows = _csv_to_rows(
            _read("workfile_config/custom_tables/custom_tables.csv")
        )
        for row in state.custom_table_rows:
            ref = row.get("table_type_ref", "")
            py_path = f"workfile_config/custom_tables/{ref}.py"
            if ref and py_path in names:
                state.custom_table_code[ref] = _read(py_path)

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
            state.file_version_id = info.get("file_version_id", "")

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
        state.settings["table_order"] = "|".join(state.table_order)
        _write("workfile_config/settings.csv",      _dict_to_key_value_csv(state.settings))

        # workfile_config/tables/ — every population-level table, one CSV each
        for table_name, rows in state.tables.items():
            _write(f"workfile_config/tables/{table_name}.csv", _rows_to_csv(rows))

        # running_order — derive fieldnames from rows if present
        if state.running_order_rows:
            from chartgen.output_generation.definition.running_order import COLUMNS
            _write("workfile_config/running_order.csv",
                   _rows_to_csv(state.running_order_rows, COLUMNS))
        else:
            _write("workfile_config/running_order.csv", "")

        # workfile_config/text_stats.csv — stat tags
        _write("workfile_config/text_stats.csv",
               _rows_to_csv(state.text_stats_rows, TEXT_STATS_FIELDNAMES))

        # workfile_config/chart_store.csv -- Chart Store
        _write("workfile_config/chart_store.csv",
               _rows_to_csv(state.chart_store_rows, CHART_STORE_FIELDNAMES))

        # workfile_config/output_tables/ -- index plus one grid CSV per table_id
        _write("workfile_config/output_tables/output_tables.csv",
               _rows_to_csv(state.output_table_rows, OUTPUT_TABLE_FIELDNAMES))
        for table_id, grid_rows in state.output_tables.items():
            _write(f"workfile_config/output_tables/{table_id}.csv", _rows_to_csv(grid_rows))

        # data_cache/
        _write("data_cache/manifest.csv",
               _rows_to_csv(state.manifest_rows, MANIFEST_FIELDNAMES))
        for fname, json_str in state.cache.items():
            zf.writestr(f"data_cache/{fname}", json_str.encode("utf-8"))

        # workfile_config/custom_charts/ — index plus one .py per row, one
        # folder per shape_type, mirroring the built-in Base Charts' own
        # folder-per-shape layout.
        _write("workfile_config/custom_charts/custom_charts.csv",
               _rows_to_csv(state.custom_chart_rows, CUSTOM_CHART_FIELDNAMES))
        for row in state.custom_chart_rows:
            ref = row.get("base_chart_name", "")
            shape = row.get("shape_type", "")
            code = state.custom_chart_code.get(ref, "")
            if ref:
                _write(f"workfile_config/custom_charts/{shape}/{ref}.py", code)

        # workfile_config/custom_tables/ -- index plus one .py per row,
        # directly at workfile_config/custom_tables/{table_type_ref}.py
        _write("workfile_config/custom_tables/custom_tables.csv",
               _rows_to_csv(state.custom_table_rows, CUSTOM_TABLE_FIELDNAMES))
        for row in state.custom_table_rows:
            ref = row.get("table_type_ref", "")
            code = state.custom_table_code.get(ref, "")
            if ref:
                _write(f"workfile_config/custom_tables/{ref}.py", code)

        # template/
        if state.template_pptx_bytes:
            workfile_name = state.workfile_name or "template"
            zf.writestr(f"template/{workfile_name}.pptx", state.template_pptx_bytes)

        # workfile_info.json — uncompressed
        info = {
            "workfile_name":     state.workfile_name,
            "last_saved_by":     state.last_saved_by,
            "last_saved_at":     state.last_saved_at,
            "chartgen_version":  get_software_id(),
            "locked_by":         state.locked_by,
            "locked_at":         state.locked_at,
            "file_version_id":   get_file_version_written(),
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
    Caller populates settings / tables / table_order etc. before first save.
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
            "workfile_config/running_order.csv",
        ]:
            zf.writestr(name, b"")
        # empty manifest table (header only)
        zf.writestr("data_cache/manifest.csv",
                    _rows_to_csv([], MANIFEST_FIELDNAMES).encode("utf-8"))
        # workfile_info
        info = {
            "workfile_name":    workfile_name,
            "last_saved_by":    "",
            "last_saved_at":    "",
            "chartgen_version": get_software_id(),
            "locked_by":        "",
            "locked_at":        "",
            "file_version_id":  get_file_version_written(),
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


# ---------------------------------------------------------------------------
# Master table
# ---------------------------------------------------------------------------

def master_table_rows(state: WorkfileState) -> list:
    """
    Return the rows of the master table — whichever table sits first in
    table_order. The master table drives the reporting unit picker and the
    batch loop. Returns [] if no tables exist yet.
    """
    if not state.table_order:
        return []
    return state.tables.get(state.table_order[0], [])
