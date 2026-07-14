"""
chart_type_map.py
Loads the static config mapping data shapes to valid chart type references.
"""

import csv
import os

MAP_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static_config", "chart_type_map.csv"
)


def get_valid_chart_types(shape_type):
    """Return list of (chart_type_ref, description) tuples valid for the given shape_type."""
    results = []
    with open(MAP_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["data_shape"] == shape_type:
                results.append((row["chart_type_ref"], row["description"]))
    return results


def get_chart_types_by_shape():
    """Return the full data_shape -> [chart_type_ref, ...] mapping from the static config."""
    mapping = {}
    with open(MAP_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            shape = row.get("data_shape", "").strip()
            ref   = row.get("chart_type_ref", "").strip()
            if shape and ref:
                mapping.setdefault(shape, []).append(ref)
    return mapping
