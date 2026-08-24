"""
chart_store.py
The Chart Store: a flat, unordered set of independently-authored chart-defs,
for use as chart components inside Output Table cells. Independent of the
Running Order, and with no position concept of its own.

A row carries the same fields as CHART_SANDBOX_FIELDS, plus its own
chart_store_id and an optional description. Authored from the same Charts
sheet sandbox a Running Order row is, as a third entry point.

Ids come from settings["next_chart_store_id"], its own counter key.
"""

from dataclasses import replace

from chartgen.shared.infrastructure.id_generation import next_unique_id
from chartgen.output_generation.execution.charts.cache_reader import load_shape
from chartgen.shared.normalisation_containers.cut_resolution import prepare_chart_cut
from chartgen.shared.normalisation_containers.population_layers import build_population_layers


def next_chart_store_id(settings: dict, ids_in_use) -> str:
    """
    Issue and persist the next Chart Store id — "C" followed by a base-36
    counter (shared encoding with Stat Tags' and Output Tables' own
    counters -- see chartgen.shared.infrastructure.id_generation -- but its
    own counter key, so the id spaces never collide or interleave). The
    "C" prefix disambiguates a Chart Store id from a Stat Tag ("T" prefix)
    when both are used inside the same Output Table cell grammar.

    ids_in_use -- every chart_store_id currently on a row. Required: an id
    reused from another row would make a "{Cn}" marker in an Output Table
    cell ambiguous, and the counter alone cannot rule that out, since a row
    uploaded via chart_store_xlsx.py carries whatever id the person typed
    and never advances the counter. next_unique_id checks the candidate
    against these rather than decoding them, so an id typed as "AB1" is
    honoured as readily as "C1".
    """
    return next_unique_id(settings, "next_chart_store_id", "C", ids_in_use)


def chart_store_row_label(row: dict, label_by_cache_file: dict) -> str:
    """
    Human-readable label for one Chart Store row, for use in selectboxes --
    mirrors charts_tab/sheet.py's own ro_row_label for a Running Order row,
    field for field, since a Chart Store entry carries the same
    base_chart_name/cache_file pair.
    """
    cache_label = label_by_cache_file.get(str(row.get("cache_file", "") or ""), row.get("cache_file", "") or "— no data —")
    ctype = str(row.get("base_chart_name", "") or "— no chart type —")
    desc = str(row.get("description", "") or "").strip()
    base = f"{row.get('chart_store_id', '')}: {ctype} · {cache_label}"
    return f"{base} — {desc}" if desc else base


def resolve_chart_store_population_layers(chart_store_row: dict, workfile_state, full_unit_set: dict) -> list:
    """
    Resolve a Chart Store entry's own population_layers against the
    current reporting context, independent of actually rendering it --
    shared by the Output Tables Preview splice
    (output_tables_tab/chart_cells.py::_render_chart_store_chart_preview) and the
    Custom Tables bundle's own optional chart-detail export
    (custom_tables/bundle.py), so the same cache-load / cut /
    population-default-fallback / layer-build pipeline is written once,
    not duplicated a third time.

    No AssemblyContext involved -- both callers run from a Streamlit tab,
    not a report assembly run, so a blank populations field is resolved
    against the workfile's own set_default_populations Running Order row
    directly, the same fallback charts_tab/preview.py uses.
    Returns [] on any
    resolution failure (missing cache_file, a cache load error, an
    unresolvable cut) -- callers treat that the same way as "nothing to
    show", never raise.
    """
    cache_file = str(chart_store_row.get("cache_file", "") or "").strip()
    if not cache_file:
        return []

    try:
        data_shape, shape_type = load_shape(cache_file, workfile_state)
    except Exception:
        return []

    start_period = str(chart_store_row.get("start_period", "") or "").strip()
    end_period = str(chart_store_row.get("end_period", "") or "").strip()
    metric_periods_str = str(chart_store_row.get("metric_periods", "") or "").strip()

    try:
        data_shape, _, target_rows, selected_ids = prepare_chart_cut(
            data_shape, shape_type, start_period, end_period, metric_periods_str,
            workfile_state.tables, workfile_state.table_order, full_unit_set,
        )
    except Exception:
        # Genuinely unexpected failures only now (e.g. a malformed cut) --
        # an unresolvable metric_periods id does not raise here (see
        # time_series_to_numeric_series' own docstring); it comes through
        # as a real metric with no data. Callers of this function treat
        # any resolution failure the same as "nothing to show" (this
        # function's own docstring), so still returning [] here rather
        # than propagating.
        return []

    # A blank populations field means "inherit the Running Order default"
    # -- see resolve_chart_store_population_layers' own docstring.
    populations_str = str(chart_store_row.get("populations", "") or "").strip()
    if not populations_str:
        for ro_row in workfile_state.running_order_rows:
            if str(ro_row.get("function", "")).strip() == "set_default_populations":
                default_pop = str(ro_row.get("populations", "") or "").strip()
                if default_pop:
                    populations_str = default_pop
                break

    try:
        population_layers = build_population_layers(
            data_shape, populations_str, target_rows, selected_ids
        )
    except Exception:
        population_layers = []
    if not population_layers:
        population_layers = [replace(data_shape, population_label="All")]
    return population_layers
