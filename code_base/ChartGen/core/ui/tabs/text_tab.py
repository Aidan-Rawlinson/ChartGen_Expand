"""
text_tab.py
Text tab — two independent tag tables:

  - Text tags — per-unit facts (e.g. [selected-reporting-unit-name]),
    resolved straight off ReportContext. One value per reporting unit,
    globally unique, presentation-wide.

  - Stat tags — short, permanent ids (e.g. [T3], [Ta7]) each standing in for
    one summary-stats value from one chart's own independently-authored
    cut of its cached data (hex_id + its own single-population/period
    fields + which Reference id). Not tied to any Running Order row — see
    Decisions.md. Genuinely a different kind of thing from the table
    above: a Reference id isn't globally unique (shapes/reference_ids.py),
    so a stat tag needs hex_id + population + reference_id to mean
    anything, where a text tag needs nothing beyond its own literal
    string.

Both tables are read by update_text (core.output_generation.execution.text)
at generation time; this tab only defines/previews them.
"""

import os

import pandas as pd
import streamlit as st

from core.acquisition.toolkit_nhs.peer_groups import get_peer_group_value_options
from core.output_generation.definition.running_order import (
    build_populations_options, build_metric_periods_string,
)
from core.output_generation.execution.charts.cache_reader import cache_files_sorted_by_chart_ref
from core.output_generation.execution.text.stat_tags import next_stat_tag, resolve_stat_tag_value, layer_display_label
from core.output_generation.execution.text.stat_tags_xlsx import (
    write_stat_tags_xlsx, read_stat_tags_xlsx, assign_missing_tags,
)
from core.shared.infrastructure.cg_extracts import get_extracts_folder
from core.shared.infrastructure.report_context import build_report_context
from core.shared.infrastructure.soft_parents import resolve_full_unit_set
from core.shared.infrastructure.value_formatting import format_reference_value
from core.shared.normalisation_containers.cut_resolution import prepare_chart_cut
from core.shared.normalisation_containers.population_layers import build_population_layers
from core.shared.normalisation_containers.shapes import (
    apply_period_range, summary_stats, reference_rows_for_shape_type,
)
from core.ui.common.compact_layout import tight_divider, tight_subheader, tight_caption
from core.ui.common.guidance import render_tab_header
from core.ui.common.pickers import pick_xlsx_file
from core.workfile.state.session_state import (
    settings, master_table, cached_files, manifest, load_shape_ps, ws,
)

CHART_PLACEHOLDER = "- Select a chart -"


def _multiselect_prepare(widget_key: str, record_key: str, options: list) -> None:
    """
    Rescue a multiselect's widget key from its persisted "record" key
    (widget_key + "_record") only when this render's options have actually
    changed shape since last render (or on first use) — never
    unconditionally. Overwriting the widget's live value on every render
    would discard the very thing Streamlit just wrote into it a moment
    ago: when the user ticks something, Streamlit updates
    st.session_state[widget_key] to the new value *before* the script
    reruns, so on that rerun the "current" value already *is* the fresh
    tick — stomping it here would silently undo every interaction.

    Rescue only fires when the options list genuinely changed (or the
    widget's current value would no longer be valid against it, which
    Streamlit would otherwise raise on) — e.g. switching Chart to one with
    a different set of period ids. In that case the widget is reset to
    whatever in the persisted record is valid for the new options, which
    is what lets a previously-ticked value reappear ticked once it's
    offered again, without ever being force-applied while it was already
    being interacted with normally.
    """
    st.session_state.setdefault(record_key, [])
    record = set(st.session_state[record_key])

    prev_options_key = widget_key + "_prev_options"
    prev_options = st.session_state.get(prev_options_key)
    current_value = st.session_state.get(widget_key, [])

    options_changed = (set(prev_options or []) != set(options))
    stale_value_present = any(v not in options for v in current_value)

    if widget_key not in st.session_state or options_changed or stale_value_present:
        st.session_state[widget_key] = [o for o in options if o in record]

    st.session_state[prev_options_key] = list(options)


def _multiselect_reconcile(widget_key: str, record_key: str, options: list):
    """
    After a multiselect renders, fold this render's outcome into its
    persisted record: everything ticked now (the widget's live value) is
    remembered; everything actually offered this render (options) but not
    ticked is forgotten — an explicit non-selection, whether just unticked
    or never selected while visible. Anything not offered this render
    (temporarily unavailable) is untouched either way, so it survives to
    be re-offered, and re-ticked automatically, once it reappears. Exact
    string match throughout — nothing guessed, expanded, or fuzzy-matched.
    """
    record = set(st.session_state[record_key])
    options_set = set(options)
    new_value = set(st.session_state[widget_key])
    record = (record - (options_set - new_value)) | new_value
    st.session_state[record_key] = list(record)


def render_text_tab():
    render_tab_header("Text replacement tables", "text")

    workfile_state = ws()
    the_settings = settings()
    units = master_table()
    rc = build_report_context(the_settings, units)

    # --- Text tags (per-unit) ---
    tight_caption(
        "These tables are used to support text replacements on the PowerPoint template "
        "and in tables that we wish to create for the report. Please include update_text "
        "in the running order to apply the replacements during output creation."
    )

    tight_divider()
    tight_subheader("Report level text replacement tags")
    preview_value = rc.unit_name if rc else "— no reporting unit selected —"
    st.dataframe(
        {
            "Text Tag": ["[selected-reporting-unit-name]"],
            "Replaced with": ["Unit name"],
            "Current value": [preview_value],
        },
        use_container_width=True, hide_index=True,
    )

    tight_divider()

    # --- Full Unit Set for the current reporting unit — shared by both the
    # "define a new tag" preview below and the existing tags' live values,
    # built once rather than per tag. ---
    master_table_name = workfile_state.table_order[0] if workfile_state.table_order else ""
    reporting_row = (
        next((r for r in units if str(r["unit_id"]) == rc.unit_id), None) if rc else None
    )
    full_unit_set = (
        resolve_full_unit_set(reporting_row, master_table_name, workfile_state.tables)
        if reporting_row is not None else {}
    )

    tight_subheader("Statistic text replacement tags")

    the_cached_files = cached_files()
    the_manifest = manifest()
    the_cached_files = cache_files_sorted_by_chart_ref(the_cached_files, the_manifest)

    if not the_cached_files:
        st.info("No cached chart data found. Use the Imports tab to fetch data first.")
    else:
        def file_label(f):
            entry = the_manifest.get(f, {})
            title = str(entry.get("chart_title", "")).strip()
            ref = str(entry.get("chart_ref", "")).strip()
            if title and title != "...":
                return f"{ref or f}  —  {title}"
            return ref or f

        file_options = {file_label(f): f for f in the_cached_files}

        with st.expander("Define new stat tag(s)", expanded=False):
            st.session_state.setdefault("ts_chart_choice", CHART_PLACEHOLDER)
            chart_choice = st.selectbox(
                "Chart", options=[CHART_PLACEHOLDER] + list(file_options.keys()),
                key="ts_chart_choice",
            )

            if chart_choice != CHART_PLACEHOLDER:
                selected_file = file_options[chart_choice]
                hex_id = str(the_manifest.get(selected_file, {}).get("hex_id", "") or "")
                shape, shape_type = load_shape_ps(selected_file)

                # --- Period range and metric-periods conversion (TimeSeries
                # only) — same cascade as the Charts sheet, since knowing
                # the shape type (and, for metric_periods, the resulting
                # NumericSeries snapshot) determines the reference id set
                # available to tag. ---
                start_period = ""
                end_period = ""
                metric_period_ids = []
                if shape_type == "TimeSeries" and shape.periods:
                    period_ids = [p.period_id for p in shape.periods]
                    label_by_period_id = {p.period_id: p.period_label for p in shape.periods}
                    st.session_state.setdefault("ts_start_period", "")
                    st.session_state.setdefault("ts_end_period", "")
                    if st.session_state["ts_start_period"] not in ([""] + period_ids):
                        st.session_state["ts_start_period"] = ""
                    if st.session_state["ts_end_period"] not in ([""] + period_ids):
                        st.session_state["ts_end_period"] = ""

                    def _period_format(v):
                        return "(full range)" if v == "" else label_by_period_id.get(v, v)

                    pc1, pc2 = st.columns(2)
                    with pc1:
                        st.caption("Start period")
                        start_period = st.selectbox(
                            "Start period", options=[""] + period_ids, format_func=_period_format,
                            key="ts_start_period", label_visibility="collapsed",
                        )
                    with pc2:
                        st.caption("End period")
                        end_period = st.selectbox(
                            "End period", options=[""] + period_ids, format_func=_period_format,
                            key="ts_end_period", label_visibility="collapsed",
                        )

                    # Widget-options-only trim — mirrors what prepare_chart_cut
                    # will do to the real shape below; needed here only so
                    # the Convert-to-Metrics multiselect offers the periods
                    # actually left in range.
                    _widget_scope_shape = shape
                    if start_period or end_period:
                        _widget_scope_shape = apply_period_range(shape, start_period, end_period)
                    period_ids_in_scope = [p.period_id for p in _widget_scope_shape.periods]
                    label_by_period_id_in_scope = {p.period_id: p.period_label for p in _widget_scope_shape.periods}
                    _multiselect_prepare("ts_metric_periods", "ts_metric_periods_record", period_ids_in_scope)
                    st.caption("Convert to metrics (optional)")
                    metric_period_ids = st.multiselect(
                        "Convert to metrics", options=period_ids_in_scope,
                        format_func=lambda v: label_by_period_id_in_scope.get(v, v),
                        key="ts_metric_periods", label_visibility="collapsed",
                    )
                    _multiselect_reconcile("ts_metric_periods", "ts_metric_periods_record", period_ids_in_scope)

                metric_periods_str = build_metric_periods_string(metric_period_ids)

                # --- Resolve this cut of the data shape — period-range
                # trim, metric-periods conversion, and population-table/
                # target-rows/selected-ids resolution, shared with
                # insert_chart and the Charts sheet
                # (cut_resolution.prepare_chart_cut). An unresolvable
                # metric_periods id no longer raises here (see
                # time_series_to_numeric_series' own docstring) — the
                # resulting Reference id simply carries no data, same as
                # any other missing value. ---
                shape, effective_shape_type, target_rows, selected_ids = prepare_chart_cut(
                    shape, shape_type, start_period, end_period, metric_periods_str,
                    workfile_state.tables, workfile_state.table_order, full_unit_set,
                )

                # --- Population — a single token, not a multiselect. A stat
                # tag resolves to one value, so it only ever needs one
                # population, not an ordered set of layers the way a
                # chart's populations string does. ---
                peer_options = get_peer_group_value_options(target_rows)
                pop_options = build_populations_options(peer_options)

                st.session_state.setdefault("ts_population_token", "")
                if st.session_state["ts_population_token"] not in ([""] + pop_options):
                    st.session_state["ts_population_token"] = ""
                st.caption("Population")
                populations_str = st.selectbox(
                    "Population", options=[""] + pop_options,
                    format_func=lambda v: "- Select a population -" if v == "" else v,
                    key="ts_population_token", label_visibility="collapsed",
                )

                if not populations_str:
                    st.caption("Select a population to preview available tags.")
                else:
                    try:
                        pop_layers = build_population_layers(shape, populations_str, target_rows, selected_ids)
                    except Exception as e:
                        pop_layers = []
                        st.error(f"Could not resolve population: {e}")

                    if pop_layers:
                        layer = pop_layers[0]
                        stats = summary_stats(layer)
                        rows_by_series = reference_rows_for_shape_type(effective_shape_type, stats)
                        ref_rows = [r for series_rows in rows_by_series.values() for r in series_rows]

                        st.caption(f"Population: {layer_display_label(populations_str, layer.population_label)}")

                        tag_options = [r["id"] for r in ref_rows]
                        label_by_option = {r["id"]: f"{r['label']}  [{r['id']}]" for r in ref_rows}

                        st.caption("Select which statistics to generate tags for")
                        _multiselect_prepare("ts_new_tags_selected", "ts_new_tags_selected_record", tag_options)
                        selected_tags = st.multiselect(
                            "Tags to generate", options=tag_options,
                            format_func=lambda o: label_by_option.get(o, str(o)),
                            key="ts_new_tags_selected", label_visibility="collapsed",
                        )
                        _multiselect_reconcile("ts_new_tags_selected", "ts_new_tags_selected_record", tag_options)

                        if st.session_state.pop("ts_clear_description", False):
                            st.session_state["ts_description"] = ""
                        st.caption("Description (optional)")
                        description = st.text_input(
                            "Description", key="ts_description", label_visibility="collapsed",
                            help="Free text, for your own reference only — applied to every tag "
                                 "generated below in this click.",
                        )

                        if st.button("➕  Add selected tag(s)", type="primary", disabled=not selected_tags):
                            for ref_id in selected_tags:
                                tag = next_stat_tag(the_settings)
                                workfile_state.text_stats_rows.append({
                                    "tag": tag,
                                    "hex_id": hex_id,
                                    "populations": populations_str,
                                    "start_period": start_period,
                                    "end_period": end_period,
                                    "metric_periods": metric_periods_str,
                                    "reference_id": ref_id,
                                    "description": description,
                                })
                            workfile_state.dirty = True
                            st.session_state["ts_clear_description"] = True
                            st.success(f"Added {len(selected_tags)} tag(s).")
                            st.rerun()

    # --- Existing stat tags — read-only list, live-valued, delete only ---
    stat_rows = workfile_state.text_stats_rows
    if not stat_rows:
        st.caption("No stat tags defined yet.")
        return

    def _chart_label_for_hex(hex_id):
        entry = the_manifest.get(f"{hex_id}.json", {})
        title = str(entry.get("chart_title", "")).strip()
        ref = str(entry.get("chart_ref", "")).strip()
        if title and title != "...":
            return f"{ref or hex_id}  —  {title}"
        return ref or hex_id

    display_tags, display_charts, display_layers, display_stats, display_values, display_descriptions = (
        [], [], [], [], [], []
    )
    for stat_row in stat_rows:
        display_tags.append(f"[{stat_row.get('tag', '')}]")
        display_charts.append(_chart_label_for_hex(stat_row.get("hex_id", "")))
        display_descriptions.append(stat_row.get("description", ""))
        resolved = resolve_stat_tag_value(stat_row, workfile_state, full_unit_set)
        if resolved is None:
            display_layers.append(
                layer_display_label(stat_row.get("populations", ""), "?")
            )
            display_stats.append(stat_row.get("reference_id", ""))
            display_values.append("— unresolved —")
        else:
            display_layers.append(resolved.get("layer_display", ""))
            display_stats.append(resolved.get("label", stat_row.get("reference_id", "")))
            display_values.append(
                format_reference_value(resolved["value"], resolved["kind"], resolved["format_modifier"])
            )

    selection = st.dataframe(
        pd.DataFrame({
            "Tag": display_tags,
            "Data Source": display_charts,
            "Population": display_layers,
            "Statistic": display_stats,
            "Current value": display_values,
            "Description": display_descriptions,
        }),
        use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "Tag": st.column_config.Column(width=35),
            "Population": st.column_config.Column(width=60),
            "Statistic": st.column_config.Column(width="small"),
            "Current value": st.column_config.Column(width=60),
            "Data Source": st.column_config.Column(width="small"),
        },
    )
    selected_rows = selection.selection.get("rows", [])
    sel_idx = selected_rows[0] if selected_rows else None

    col_del, col_dl, col_ul = st.columns([1, 1, 1])

    if col_del.button("🗑  Delete selected tag", disabled=(sel_idx is None), use_container_width=True):
        del workfile_state.text_stats_rows[sel_idx]
        workfile_state.dirty = True
        st.rerun()

    extracts_dir = get_extracts_folder(workfile_state.workfile_path)

    if col_dl.button("⬇  Export Stat Tags", use_container_width=True, key="ts_export_btn"):
        export_path = os.path.join(extracts_dir, "stat_tags.xlsx")
        write_stat_tags_xlsx(stat_rows, export_path)
        st.success(f"Exported to {export_path}")

    if col_ul.button("⬆  Import Stat Tags", use_container_width=True, key="ts_import_btn"):
        picked_path = pick_xlsx_file(extracts_dir, "Select edited Stat Tags Excel file")
        if picked_path:
            imported_rows = read_stat_tags_xlsx(picked_path)
            workfile_state.text_stats_rows = assign_missing_tags(imported_rows, the_settings)
            workfile_state.dirty = True
            st.rerun()
