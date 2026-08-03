"""
chart_store.py
Defines the Chart Store: a flat, unordered set of independently-authored
chart-defs (workfile_config/chart_store.csv, WorkfileState.chart_store_rows),
for use as chart components inside Output Table cells (sparklines, grid
layouts, etc) -- independent of the Running Order, which is strictly a
sequence of report content with its own position/sequence concept a Chart
Store entry deliberately has none of.

A Chart Store row carries the same fields the Charts sheet already
round-trips to an insert_chart Running Order row (CHART_SANDBOX_FIELDS --
base_chart_name, cache_file, populations, start_period/end_period/
metric_periods, width_emu/height_emu, tweaks), plus its own chart_store_id
and an optional free-text description. It is authored, previewed, and
edited from the same Charts sheet sandbox a Running Order row is -- a
third, always-available entry point alongside "Running Order row" and
"Data shape" (Decisions.md).

Chart Store ids are issued from a persisted, monotonically increasing
counter (settings["next_chart_store_id"]), the same base-36 encoding as
Stat Tags/Output Tables but its own counter key -- see
core.shared.infrastructure.id_generation.
"""

from core.shared.infrastructure.id_generation import next_id, from_base36


def next_chart_store_id(settings: dict, existing_ids=None) -> str:
    """
    Issue and persist the next Chart Store id — "C" followed by a base-36
    counter (shared encoding with Stat Tags' and Output Tables' own
    counters -- see core.shared.infrastructure.id_generation -- but its
    own counter key, so the id spaces never collide or interleave). The
    "C" prefix disambiguates a Chart Store id from a Stat Tag ("T" prefix)
    when both are used inside the same Output Table cell grammar.

    existing_ids -- every chart_store_id currently on a row, if known to
    the caller. This is a two-way flow: the system can't assume its own
    persisted counter is still the true maximum, because ids can also
    arrive from outside it (a row uploaded via chart_store_xlsx.py with
    its own id already filled in never advances the counter). So a new id
    is never issued from the stored counter alone -- the counter is first
    resynced to whatever the actual current maximum among existing_ids
    is, if that's higher, and only then incremented. Confirmed
    duplicate-id behaviour otherwise: a stale counter can silently reissue
    an id already in use on another row.
    """
    if existing_ids:
        current = int(settings.get("next_chart_store_id", "0") or "0")
        highest = current
        for eid in existing_ids:
            suffix = str(eid or "")
            if suffix.startswith("C"):
                suffix = suffix[1:]
            if not suffix:
                continue
            try:
                highest = max(highest, from_base36(suffix))
            except ValueError:
                continue  # not a base-36 id this counter ever issued -- ignore, don't let it break resync
        if highest > current:
            settings["next_chart_store_id"] = str(highest)
    return "C" + next_id(settings, "next_chart_store_id")


def chart_store_row_label(row: dict, label_by_cache_file: dict) -> str:
    """
    Human-readable label for one Chart Store row, for use in selectboxes --
    mirrors charts_tab.py's own ro_row_label for a Running Order row,
    field for field, since a Chart Store entry carries the same
    base_chart_name/cache_file pair.
    """
    cache_label = label_by_cache_file.get(str(row.get("cache_file", "") or ""), row.get("cache_file", "") or "— no data —")
    ctype = str(row.get("base_chart_name", "") or "— no chart type —")
    desc = str(row.get("description", "") or "").strip()
    base = f"{row.get('chart_store_id', '')}: {ctype} · {cache_label}"
    return f"{base} — {desc}" if desc else base
