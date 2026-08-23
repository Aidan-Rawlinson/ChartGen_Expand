"""
stat_tags.py
Defines and resolves Stat Tags: short, permanent ids ("T" plus a base-36
counter) standing in for one summary-stats value from one chart's own data.
Read by update_text, previewed on the Text tab. The "T" prefix
disambiguates a Stat Tag from a Chart Store id when both appear in the same
Output Table cell grammar.

A tag's row carries everything needed to reproduce the exact filtered shape
a Base Chart would see for one population: hex_id, its own populations
string, its own period fields, and which reference id to read. Anchored on
hex_id, never chart_ref, which renumbers whenever the manifest changes.

A tag's populations string is restricted to a single token, enforced by a
selectbox rather than a multiselect: a tag resolves to one value, so
build_population_layers always returns exactly one layer and there is
nothing to track beyond it.

The cut pipeline is shared with insert_chart and the Charts sheet via
cut_resolution. This module adds only the cache-loading step specific to how
a tag identifies its chart, and the final reference-id lookup within the one
resulting layer.

Tag ids come from a persisted, monotonically increasing counter, never
recomputed from surviving rows: recomputing after a delete would let a fresh
tag reuse an id some untouched piece of template text still points at.
"""

from chartgen.output_generation.execution.charts.cache_reader import load_shape
from chartgen.shared.infrastructure.id_generation import next_id, from_base36
from chartgen.shared.normalisation_containers.cut_resolution import prepare_chart_cut
from chartgen.shared.normalisation_containers.peer_group_tokens import parse_peer_token
from chartgen.shared.normalisation_containers.population_layers import build_population_layers
from chartgen.shared.normalisation_containers.shapes import summary_stats, reference_rows_for_shape_type


def next_stat_tag(settings: dict, existing_ids=None) -> str:
    """
    Issue and persist the next stat tag id — "T" followed by a base-36
    counter (shared encoding with Output Tables' own table_id counter and
    Chart Store's own chart_store_id — see
    chartgen.shared.infrastructure.id_generation — but its own counter key, so
    the id spaces never collide or interleave). The "T" prefix disambiguates
    a Stat Tag from a Chart Store id ("C" prefix) when both are used inside
    the same Output Table cell grammar — not needed for the
    counter itself, which already has its own key.

    existing_ids -- every tag currently on a row, if known to the caller.
    The persisted counter cannot be assumed to be the true maximum, because
    tags also arrive from outside it: a row imported via stat_tags_xlsx.py
    with its own tag already filled in never advances the counter. So a new
    tag is never issued from the stored counter alone -- the counter is
    first resynced to the actual maximum among existing_ids, if that is
    higher, and only then incremented. Without this a stale counter
    silently reissues a tag already in use, and template text still
    pointing at the original resolves to the new row's value.
    """
    if existing_ids:
        current = int(settings.get("next_stat_tag_id", "0") or "0")
        highest = current
        for eid in existing_ids:
            suffix = str(eid or "")
            if suffix.startswith("T"):
                suffix = suffix[1:]
            if not suffix:
                continue
            try:
                highest = max(highest, from_base36(suffix))
            except ValueError:
                continue  # not a base-36 id this counter ever issued -- ignore, don't let it break resync
        if highest > current:
            settings["next_stat_tag_id"] = str(highest)
    return "T" + next_id(settings, "next_stat_tag_id")


def layer_display_label(populations_str: str, resolved_population_label: str) -> str:
    """
    Human-readable label for a stat tag's single population token.

    "All", "Selected", and "Name(Value)" tokens are shown as their own
    literal token text — already static and self-describing, identical to
    resolved_population_label in practice. A "Name()" (empty-bracket)
    token is shown as "Name() — <resolved_population_label>" instead of
    either just the token (uninformative — doesn't say which group it
    currently means) or just the resolved value alone (looks identical to
    a static Name(Value) reference, which it is not — the resolved value
    tracks whoever is currently selected, e.g. "South East" today, a
    different region tomorrow for a different organisation).
    """
    token = (populations_str or "").strip()
    if not token:
        return resolved_population_label
    parsed = parse_peer_token(token)
    if parsed is not None and parsed[1] == "":
        return f"{token} — {resolved_population_label}"
    return token


def resolve_stat_cut(hex_id: str, populations_str: str, start_period: str, end_period: str,
                     metric_periods_str: str, workfile_state, full_unit_set: dict):
    """
    Reproduce one stat tag's own cut of a chart's cached data. Loads the
    shape from the cache (the one step specific to stat tags — a bare
    hex_id rather than a Running Order row's or the Charts sheet's own
    cache_file/selected_file), then hands off to
    cut_resolution.prepare_chart_cut for the pipeline shared with
    insert_chart and the Charts sheet, then build_population_layers.

    Returns (population_layers, effective_shape_type) — effective meaning
    "NumericSeries" rather than the cache's own "TimeSeries" once a
    metric_periods conversion has actually been applied.
    population_layers holds at most one entry, since populations_str is a
    single token (see module docstring). An empty list / "" signals the
    cut couldn't be resolved at all (missing cache file, bad period range,
    etc) — callers here treat that as "tag unresolved," not an error to
    raise.
    """
    cache_file = f"{hex_id}.json"
    if not hex_id or cache_file not in workfile_state.cache:
        return [], ""

    try:
        data_shape, shape_type = load_shape(cache_file, workfile_state)
    except Exception:
        return [], ""

    try:
        data_shape, effective_shape_type, target_rows, selected_ids = prepare_chart_cut(
            data_shape, shape_type, start_period, end_period, metric_periods_str,
            workfile_state.tables, workfile_state.table_order, full_unit_set,
        )
    except Exception:
        # An unresolvable metric_periods id does not raise here (see
        # time_series_to_numeric_series' own docstring) — the resulting
        # Reference id simply carries no data, resolved further down as
        # "-" the same as any other missing value, rather than the whole
        # tag going unresolved. Genuinely unexpected failures only now.
        return [], shape_type

    population_layers = []
    if populations_str:
        try:
            population_layers = build_population_layers(
                data_shape, populations_str, target_rows, selected_ids
            )
        except Exception:
            population_layers = []

    return population_layers, effective_shape_type


def resolve_stat_tag_value(row: dict, workfile_state, full_unit_set: dict):
    """
    Resolve one text_stats.csv row to {"value", "kind", "format_modifier",
    "label", "layer_display"} for the current reporting unit, or None if
    anything in the chain can't be resolved (deleted chart, the population
    no longer resolves to anything, or reference id no longer present —
    e.g. the shape's series count changed since the tag was created).
    update_text must keep going across every tag in the presentation
    regardless of one going stale, so this never raises.
    """
    hex_id = str(row.get("hex_id", "") or "")
    if not hex_id:
        return None

    populations_str = str(row.get("populations", "") or "")
    population_layers, shape_type = resolve_stat_cut(
        hex_id, populations_str,
        str(row.get("start_period", "") or ""),
        str(row.get("end_period", "") or ""),
        str(row.get("metric_periods", "") or ""),
        workfile_state, full_unit_set,
    )
    if not population_layers:
        return None
    layer = population_layers[0]

    stats = summary_stats(layer)
    rows_by_series = reference_rows_for_shape_type(shape_type, stats)
    wanted_ref = str(row.get("reference_id", "") or "")
    for series_rows in rows_by_series.values():
        for r in series_rows:
            if r["id"] == wanted_ref:
                return {
                    "value": r["value"], "kind": r["kind"],
                    "format_modifier": layer.format_modifier, "label": r["label"],
                    "layer_display": layer_display_label(populations_str, layer.population_label),
                }
    return None
