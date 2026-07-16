"""
soft_parents.py
Generic helper for the soft_parents column shared by every population-level
table. A soft-parent relationship links a row to another table without
assuming a strict one-parent-per-row structure — a row may hold zero, one,
or several ids in a given table, and may link to any number of different
tables at once. Recorded on the child side only; the parent table carries
no reverse reference.

Format: "table_name:id1^id2|table_name:id3" — "|" separates entries for
different tables, "^" separates multiple ids within the same table.

Resolution here is deliberately one hop only: given a row, find the tables
and rows it links to directly. Nothing here follows a resolved row's own
soft_parents onward to a second hop — that's a separate step for whenever
it's actually needed, not something to fold in here.
"""


def format_soft_parents(links: dict) -> str:
    """
    Build a soft_parents cell value from {table_name: [id, id, ...]}.
    Tables with no ids are omitted from the result.
    """
    parts = []
    for table_name, ids in links.items():
        clean_ids = [str(i) for i in ids if str(i).strip()]
        if clean_ids:
            parts.append(f"{table_name}:" + "^".join(clean_ids))
    return "|".join(parts)


def parse_soft_parents(value: str) -> dict:
    """
    Parse a soft_parents cell value into {table_name: [id, id, ...]}.
    Inverse of format_soft_parents. Returns {} for a blank/empty value.
    """
    result = {}
    if not value or not str(value).strip():
        return result
    for part in str(value).split("|"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        table_name, ids_str = part.split(":", 1)
        ids = [i for i in ids_str.split("^") if i]
        if ids:
            result[table_name] = ids
    return result


def related_tables(rows: list) -> list:
    """
    Return the distinct table names a table's rows link to via soft_parents,
    one hop only. Order follows first appearance across the rows.
    """
    seen = []
    for row in rows:
        for table_name in parse_soft_parents(row.get("soft_parents", "")):
            if table_name not in seen:
                seen.append(table_name)
    return seen


def resolve_related_rows(row: dict, tables: dict) -> dict:
    """
    Resolve one row's soft_parents links into the actual rows they point to,
    one hop only. Matched by unit_id against each linked table.
    Returns {table_name: [row, row, ...]} — tables with no match are omitted.
    """
    links = parse_soft_parents(row.get("soft_parents", ""))
    resolved = {}
    for table_name, ids in links.items():
        id_set = set(ids)
        matches = [r for r in tables.get(table_name, []) if str(r.get("unit_id")) in id_set]
        if matches:
            resolved[table_name] = matches
    return resolved


def resolve_referencing_rows(row: dict, own_table_name: str, tables: dict) -> dict:
    """
    Reverse of resolve_related_rows: find rows in other tables whose
    soft_parents reference this row — i.e. rows for which this row is the
    soft-parent, rather than rows this row itself points at. One hop only.
    own_table_name is needed because soft_parents is recorded on the child
    side only; there is nothing on this row itself to search by.
    Returns {table_name: [row, row, ...]} — tables with no match are omitted.
    """
    unit_id = str(row.get("unit_id", ""))
    resolved = {}
    for table_name, rows in tables.items():
        if table_name == own_table_name:
            continue
        matches = [
            r for r in rows
            if unit_id in parse_soft_parents(r.get("soft_parents", "")).get(own_table_name, [])
        ]
        if matches:
            resolved[table_name] = matches
    return resolved


def resolve_all_related_rows(row: dict, own_table_name: str, tables: dict) -> dict:
    """
    Combine resolve_related_rows (this row's own soft_parents, forward) and
    resolve_referencing_rows (other rows pointing at this one, reverse) into
    a single one-hop related-rows map, so a table can be looked at from
    either direction — as a child or as a soft-parent. Rows reachable via
    both directions for the same table are merged without duplicates,
    compared by unit_id.
    """
    forward = resolve_related_rows(row, tables)
    reverse = resolve_referencing_rows(row, own_table_name, tables)

    combined = {}
    for table_name in set(forward) | set(reverse):
        seen_ids = set()
        merged = []
        for r in forward.get(table_name, []) + reverse.get(table_name, []):
            uid = str(r.get("unit_id", ""))
            if uid not in seen_ids:
                seen_ids.add(uid)
                merged.append(r)
        combined[table_name] = merged
    return combined


def resolve_full_unit_set(row: dict, own_table_name: str, tables: dict) -> dict:
    """
    The full one-hop unit set for a row: itself (under its own table), plus
    every row related to it in either direction (resolve_all_related_rows).

    This is the single source of truth for "which row(s) represent this same
    real-world unit in each table" — used both for display (the Select tab's
    Full Unit(s) table) and, during a batch run, for resolving which unit(s)
    a chart should treat as Selected, based on that chart's own
    population_table. A table entry can hold more than one row — that's not
    a bug to collapse; e.g. an organisation genuinely supporting two ICBs
    means the ICB entry holds two rows, and a chart against the ICB table is
    expected to highlight both.
    """
    full = {own_table_name: [row]}
    related = resolve_all_related_rows(row, own_table_name, tables)
    for table_name, rows in related.items():
        bucket = full.setdefault(table_name, [])
        seen_ids = {str(r.get("unit_id")) for r in bucket}
        for r in rows:
            uid = str(r.get("unit_id"))
            if uid not in seen_ids:
                bucket.append(r)
                seen_ids.add(uid)
    return full
