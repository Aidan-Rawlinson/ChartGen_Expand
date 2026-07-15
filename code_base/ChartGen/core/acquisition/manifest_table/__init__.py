"""
manifest_table
Excel export/import round-trip for the manifest table (data_cache/
manifest.csv) — the acquisition-side equivalent of the Running Order's
xlsx_writer/xlsx_reader pair. Schema ownership stays with
core.workfile.state.workfile_file (MANIFEST_FIELDNAMES).
"""

from core.acquisition.manifest_table.xlsx_writer import write_manifest_xlsx
from core.acquisition.manifest_table.xlsx_reader import read_manifest_xlsx, apply_manifest_import

__all__ = ["write_manifest_xlsx", "read_manifest_xlsx", "apply_manifest_import"]
