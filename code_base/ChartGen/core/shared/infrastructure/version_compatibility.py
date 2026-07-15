"""
version_compatibility.py
Owns the distinction between the software id (this installed build of
ChartGen) and the file version id (the .cgw internal structure a given
workfile was saved with) - two independent version numbers, not one.

The reference file (version_compatibility.csv) is this software build's
single source of truth for:
  - software_id            - this build's own version label
  - file_version_written   - the file version id this build writes on Save
  - file_versions_readable - semicolon-delimited list of file version ids
                              this build can still open

A workfile whose file_version_id is not in file_versions_readable is a
hard refuse at Open (Decisions.md) - no partial read, no migration attempt.
Expanding compatibility later just means adding an id to that list.
"""

import csv
import io
import os

_CSV_PATH = os.path.join(os.path.dirname(__file__), "version_compatibility.csv")


def _load() -> dict:
    with open(_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(io.StringIO(f.read()))
        return {row["key"]: row["value"].strip() for row in reader}


def get_software_id() -> str:
    return _load().get("software_id", "")


def get_file_version_written() -> str:
    """The file_version_id this build stamps into workfile_info.json on Save/New."""
    return _load().get("file_version_written", "")


def get_file_versions_readable() -> list:
    raw = _load().get("file_versions_readable", "")
    return [v.strip() for v in raw.split(";") if v.strip()]


def is_file_version_compatible(file_version_id: str) -> bool:
    """
    Hard compatibility check. An empty/missing file_version_id (an older
    workfile predating this field) is treated as incompatible, not assumed
    safe - it hasn't been through this check before.
    """
    if not file_version_id:
        return False
    return file_version_id in get_file_versions_readable()
