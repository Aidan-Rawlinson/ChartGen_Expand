"""
dialog_support.py
Row-edit dialog support: filtering chart-type options to those valid for a
row's data shape, and building/parsing the populations string in its fixed
canonical order (All -> peer groups -> Selected). Used by the Running Order
tab's row-edit dialog; kept here because both rules are about the Running
Order's own schema and validity, not about rendering.
"""

from core.output_generation.execution.charts.chart_type_map import get_chart_types_by_shape


def get_valid_chart_refs_for_cache_file(cache_file: str, manifest: dict) -> list:
    """
    Return the list of chart_type_ref values valid for the data shape of the
    given cache file, per the shape/chart-type pairing in chart_type_map.csv.
    Falls back to every chart type across all shapes if the cache file or its
    shape type is not found in the manifest.
    """
    shape_type = (manifest.get(cache_file) or {}).get("shape_type", "")
    chart_type_by_shape = get_chart_types_by_shape()
    valid_refs = chart_type_by_shape.get(shape_type, [])
    if not valid_refs:
        valid_refs = [ref for refs in chart_type_by_shape.values() for ref in refs]
    return valid_refs


def build_populations_options(peer_options: list) -> list:
    """Return the full ordered list of selectable populations-string tokens: All, then peer options, then Selected."""
    return ["All"] + list(peer_options) + ["Selected"]


def parse_populations_string(populations_str: str, valid_options: list) -> list:
    """Parse a '^'-delimited populations string into a list of tokens, dropping any not in valid_options."""
    if not populations_str:
        return []
    return [p.strip() for p in populations_str.split("^") if p.strip() and p.strip() in valid_options]


def build_populations_string(selected_tokens: list, valid_options: list) -> str:
    """
    Build a '^'-delimited populations string from a set of selected tokens,
    in the fixed canonical order (All -> peer groups -> Selected) rather than
    whatever order the tokens were selected in.
    """
    selected_set = set(selected_tokens)
    return "^".join(p for p in valid_options if p in selected_set)
