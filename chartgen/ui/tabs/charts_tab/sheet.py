"""
sheet.py
Charts sheet entry point -- a sandbox for previewing and tuning chart
rendering, wired as a two-way sync with the Running Order.

Two entry points, always both available and always convertible into each
other:
  - Running Order row (bound mode) -- loads an existing insert_chart row's
    chart-relevant fields; Overwrite defaults to that same row.
  - Data shape (free-play) -- loads a cached dataset directly, with no row
    bound; save-back always requires picking a target row explicitly.

The Charts sheet owns this flow. It reads a Running Order row and writes
back on explicit Save; the Running Order tab never pushes to it.

Round-trip fields come from CHART_SANDBOX_FIELDS rather than being
hardcoded, so extending the sync means editing that list plus the
field_value_builders map in save_back.py, not reworking this tab's load
and save.

Sizing is never edited as raw EMU. The user-facing unit is percent of the
shorter page dimension, on both entry paths, converting to EMU only at
the point of writing back.

Rows are referenced by row_id, never by list position. row_id survives an
Overwrite but not an Insert, which is why sandbox state referencing rows
is cleared after every save.

This module is the order of the sheet. Each section below is rendered by
its own module, and the sequence of those calls is load-bearing: a
Streamlit widget cannot be changed retroactively once instantiated this
pass, so a value has to be staged before the widget it targets is
created. Do not reorder these calls.
"""

from dataclasses import replace as _replace

import streamlit as st

from chartgen.acquisition.toolkit_nhs.peer_groups import get_peer_group_value_options
from chartgen.output_generation.definition.running_order import (
    get_valid_chart_refs_for_cache_file,
    build_populations_options, parse_populations_string, build_populations_string,
)
from chartgen.output_generation.execution.charts.cache_reader import cache_files_sorted_by_chart_ref
from chartgen.output_generation.execution.charts.chart_store import chart_store_row_label
from chartgen.output_generation.execution.charts.chart_type_map import get_valid_chart_types
from chartgen.output_generation.execution.charts.custom_charts import custom_chart_descriptions
from chartgen.shared.infrastructure.page_sizing import (
    percent_to_emu, get_page_size_emu,
    has_known_template_page_size, STANDARD_PAGE_SIZES_EMU, DEFAULT_STANDARD_PAGE_SIZE,
)
from chartgen.shared.infrastructure.report_context import build_report_context
from chartgen.shared.infrastructure.soft_parents import resolve_full_unit_set
from chartgen.shared.normalisation_containers.cut_resolution import prepare_chart_cut
from chartgen.shared.normalisation_containers.population_layers import build_population_layers
from chartgen.ui.common.guidance import render_tab_header
from chartgen.ui.tabs.charts_tab.authoring import _render_custom_charts, _render_export_picture
from chartgen.ui.tabs.charts_tab.chart_store_area import _render_chart_store_area
from chartgen.ui.tabs.charts_tab.constants import (
    CHART_STORE_PLACEHOLDER, CHART_STORE_TARGET_PLACEHOLDER, DEFAULT_ZOOM,
    RO_PLACEHOLDER, SHAPE_PLACEHOLDER, TARGET_PLACEHOLDER, ZOOM_OPTIONS,
)
from chartgen.ui.tabs.charts_tab.periods import _render_period_controls
from chartgen.ui.tabs.charts_tab.preview import _render_preview
from chartgen.ui.tabs.charts_tab.save_back import _render_save_back
from chartgen.ui.tabs.charts_tab.selection import _render_select_chart
from chartgen.ui.tabs.charts_tab.state import _clear_sandbox_state, _restore_charts_sheet_state
from chartgen.workfile.state.session_state import (
    settings, master_table, cached_files, manifest, load_shape_ps, ws,
)


def render_charts_tab():
    render_tab_header("Chart Review, Customisation and Formatting", "charts")

    the_cached_files = cached_files()
    the_manifest = manifest()
    the_cached_files = cache_files_sorted_by_chart_ref(the_cached_files, the_manifest)

    if not the_cached_files:
        st.info("No cached chart data found. Use the Imports tab to fetch data first.")
        return

    workfile_state = ws()
    the_settings = settings()

    # --- Full Unit Set for the current reporting unit. Needed by
    # prepare_chart_cut's selected_ids resolution below, and independent of
    # which chart is selected, so computed once here. ---
    units_for_shape = master_table()
    rc = build_report_context(the_settings, units_for_shape)
    master_table_name = workfile_state.table_order[0] if workfile_state.table_order else ""
    reporting_row = (
        next((r for r in units_for_shape if str(r["unit_id"]) == rc.unit_id), None) if rc else None
    )
    full_unit_set = (
        resolve_full_unit_set(reporting_row, master_table_name, workfile_state.tables)
        if reporting_row is not None else {}
    )

    def file_label(f):
        entry = the_manifest.get(f, {})
        title = str(entry.get("chart_title", "")).strip()
        ref = str(entry.get("chart_ref", "")).strip()
        if title and title != "...":
            return f"{ref or f}  —  {title}"
        return ref or f

    file_options = {file_label(f): f for f in the_cached_files}
    label_by_cache_file = {v: k for k, v in file_options.items()}

    ro_rows = workfile_state.running_order_rows
    row_id_to_idx = {
        r["row_id"]: i for i, r in enumerate(ro_rows) if str(r.get("function", "")) == "insert_chart"
    }
    chart_row_ids = list(row_id_to_idx.keys())

    chart_store_by_id = {r["chart_store_id"]: r for r in workfile_state.chart_store_rows}
    chart_store_ids = list(chart_store_by_id.keys())

    def format_chart_store_choice(v):
        return v if v in (CHART_STORE_PLACEHOLDER, CHART_STORE_TARGET_PLACEHOLDER) else chart_store_row_label(chart_store_by_id[v], label_by_cache_file)

    def ro_row_label(row_id):
        r = ro_rows[row_id_to_idx[row_id]]
        cache_label = label_by_cache_file.get(str(r.get("cache_file", "") or ""), r.get("cache_file", "") or "— no data —")
        ctype = str(r.get("base_chart_name", "") or "— no chart type —")
        return f"Row {row_id}: {ctype} · {cache_label}"

    def format_row_choice(v):
        return v if v == RO_PLACEHOLDER else ro_row_label(v)

    def format_target_choice(v):
        return v if v == TARGET_PLACEHOLDER else ro_row_label(v)

    # --- Restore saved sandbox state, once per workfile Open (the
    # "cs_tab_rendered" flag is cleared wholesale by clear_workfile_session_state
    # on every Open/Close, so this always fires exactly once per session per
    # workfile, then never again until the next Open). Lets a user pick up
    # where they left off after a Save + reopen, not just re-derive a bound
    # row's own stored fields. ---
    if "cs_tab_rendered" not in st.session_state:
        st.session_state["cs_tab_rendered"] = True
        _restore_charts_sheet_state(the_settings, row_id_to_idx, the_manifest, label_by_cache_file, chart_store_by_id)

    left, right = st.columns([1, 4.7])

    with left:
        ro_choice, shape_choice = _render_select_chart(
            the_settings, the_manifest, ro_rows, row_id_to_idx, chart_row_ids,
            chart_store_by_id, chart_store_ids, file_options, label_by_cache_file,
            format_row_choice, format_chart_store_choice,
        )

        if st.session_state.get("cs_show_chart_store", False):
            with right:
                _render_chart_store_area(workfile_state, the_manifest, label_by_cache_file, the_settings)
            return

        bound_row_idx = st.session_state.get("cs_bound_row_idx")

        if shape_choice == SHAPE_PLACEHOLDER:
            return

        selected_file = file_options[shape_choice]
        # Cached alongside the label-keyed widget state so
        # capture_charts_sheet_state can persist the real filename rather
        # than the display label, which isn't stable (chart_ref renumbers
        # whenever the manifest table changes).
        st.session_state["cs_selected_cache_file"] = selected_file
        shape, shape_type = load_shape_ps(selected_file)

        # --- Shape mismatch warning — bound row still targeted, nothing blocked ---
        bound_shape_type = st.session_state.get("cs_bound_shape_type")
        if bound_row_idx is not None and bound_shape_type and bound_shape_type != shape_type:
            st.warning(
                "This data is a different shape than the bound Running Order row "
                f"('{bound_shape_type}' → '{shape_type}'). Chart type will need to be reselected."
            )

        # --- Period range and metric-periods conversion (TimeSeries only) ---
        (start_period, end_period, metric_periods_str,
         start_period_to_save, end_period_to_save, metric_periods_to_save) = _render_period_controls(
            shape, shape_type, bound_row_idx, ro_rows, chart_store_by_id,
        )

        # --- Resolve this cut, via cut_resolution.prepare_chart_cut, the
        # same path insert_chart and Stat Tags use. An unresolvable
        # metric_periods id does not raise; it arrives as a metric with no
        # data, for the Base Chart to handle. ---
        shape, effective_shape_type, target_rows, selected_ids = prepare_chart_cut(
            shape, shape_type, start_period, end_period, metric_periods_str,
            workfile_state.tables, workfile_state.table_order, full_unit_set,
        )
        converts_to_metrics = (effective_shape_type != shape_type)

        # --- Chart type — filtered to this shape (or, if metric_periods
        # converted it, to NumericSeries instead), clamped before rendering ---
        valid_types = get_valid_chart_types(effective_shape_type) + custom_chart_descriptions(
            effective_shape_type, workfile_state.custom_chart_rows
        )
        if not valid_types:
            st.warning(f"No Base Charts defined for shape type '{effective_shape_type}'.")
            return
        valid_refs = get_valid_chart_refs_for_cache_file(
            selected_file, the_manifest, converts_to_metrics=converts_to_metrics,
            custom_chart_rows=workfile_state.custom_chart_rows,
        )
        # Shows base_chart_name, not the chart_type_map.csv description,
        # because base_chart_name is what appears everywhere else: the
        # Running Order dropdown, the code, the file names. The description
        # column still exists in chart_type_map.csv but is unused.

        if "cs_pending_base_chart_name" in st.session_state:
            pending_ref = st.session_state.pop("cs_pending_base_chart_name")
            st.session_state["cs_base_chart_name"] = pending_ref if pending_ref in valid_refs else ""
        if st.session_state.get("cs_base_chart_name", "") not in ([""] + valid_refs):
            st.session_state["cs_base_chart_name"] = ""
        st.session_state.setdefault("cs_base_chart_name", "")

        # Auto-expanded while no chart type is chosen yet; collapses itself
        # the moment one is picked (re-evaluated fresh each run).
        chart_settings_expanded = (st.session_state.get("cs_base_chart_name", "") == "")
        with st.expander("Select Visualisation", expanded=chart_settings_expanded):
            base_chart_name = st.selectbox(
                "Base chart", options=[""] + valid_refs,
                format_func=lambda v: "— select chart type —" if v == "" else v,
                key="cs_base_chart_name", label_visibility="collapsed",
            )

        # --- Populations ---
        peer_options = get_peer_group_value_options(target_rows)
        pop_options = build_populations_options(peer_options)

        if "cs_pending_populations_str" in st.session_state:
            pending_pop_str = st.session_state.pop("cs_pending_populations_str")
            st.session_state["cs_populations_tokens"] = parse_populations_string(pending_pop_str, pop_options)
        st.session_state.setdefault("cs_populations_tokens", [])
        # Clamp — a prior shape's population table may have offered different
        # peer-group tokens than this one does.
        st.session_state["cs_populations_tokens"] = [
            t for t in st.session_state["cs_populations_tokens"] if t in pop_options
        ]

        with st.expander("Populations", expanded=False):
            populations_tokens = st.multiselect(
                "Populations", options=pop_options, key="cs_populations_tokens",
                label_visibility="collapsed",
                help="Blank = inherit the Running Order default. Order is fixed: All → peer groups → Selected.",
            )
        populations_str = build_populations_string(populations_tokens, pop_options)

        # Fall back to the workfile default for preview only when the row's
        # own override is blank — mirrors insert_chart's own inherit rule.
        preview_populations_str = populations_str
        if not preview_populations_str:
            for ro_row in ro_rows:
                if str(ro_row.get("function", "")).strip() == "set_default_populations":
                    default_pop = str(ro_row.get("populations", "") or "").strip()
                    if default_pop:
                        preview_populations_str = default_pop
                    break

        # --- Tweaks — a free-text string passed straight through to the
        # Base Chart function's own `tweaks` parameter,
        # uninterpreted by anything in the Charts sheet or Running Order
        # layer. Populates from the bound Running Order row's tweaks
        # column when loaded that way; otherwise typed here directly. ---
        if "cs_pending_tweaks_str" in st.session_state:
            st.session_state["cs_tweaks_str"] = st.session_state.pop("cs_pending_tweaks_str")
        st.session_state.setdefault("cs_tweaks_str", "")

        with st.expander("Tweaks", expanded=False):
            tweaks_str = st.text_area(
                "Tweaks", key="cs_tweaks_str", label_visibility="collapsed",
                help="Free text passed straight through to the Base Chart function's tweaks parameter.",
            )

        # --- Sizing ---
        with st.expander("Sizing", expanded=False):
            if not has_known_template_page_size(the_settings):
                page_size_options = list(STANDARD_PAGE_SIZES_EMU.keys())
                st.session_state.setdefault("cs_manual_page_size", DEFAULT_STANDARD_PAGE_SIZE)
                st.caption("Page size")
                st.selectbox(
                    "Page size", options=page_size_options, key="cs_manual_page_size",
                    label_visibility="collapsed",
                )
            st.session_state.setdefault("cs_width_pct", 50.0)
            st.session_state.setdefault("cs_height_pct", 50.0)
            w_col, h_col = st.columns(2)
            with w_col:
                st.caption("Width")
                width_pct = st.number_input(
                    "Width", min_value=0.0, step=1.0, format="%.2f",
                    key="cs_width_pct", label_visibility="collapsed",
                )
            with h_col:
                st.caption("Height")
                height_pct = st.number_input(
                    "Height", min_value=0.0, step=1.0, format="%.2f",
                    key="cs_height_pct", label_visibility="collapsed",
                )

        page_w, page_h = get_page_size_emu(the_settings, st.session_state.get("cs_manual_page_size"))
        width_emu = percent_to_emu(width_pct, page_w, page_h)
        height_emu = percent_to_emu(height_pct, page_w, page_h)

        # --- Population layers for this preview — built once here, reused
        # by both the Custom Charts download bundle and the render call in
        # the right-hand column below. ---
        try:
            pop_layers = build_population_layers(shape, preview_populations_str, target_rows, selected_ids)
        except Exception:
            pop_layers = []
        if not pop_layers:
            pop_layers = [_replace(shape, population_label="All")]

        _render_save_back(
            workfile_state, ro_choice, chart_row_ids, chart_store_ids, row_id_to_idx,
            format_target_choice, format_chart_store_choice,
            base_chart_name, selected_file, populations_str,
            start_period_to_save, end_period_to_save, metric_periods_to_save,
            width_emu, height_emu, tweaks_str,
        )

        _render_custom_charts(
            workfile_state, base_chart_name, effective_shape_type,
            pop_layers, width_emu, height_emu, tweaks_str,
        )

        with st.expander("Zoom", expanded=False):
            st.session_state.setdefault("cs_zoom", DEFAULT_ZOOM)
            zoom_choice = st.selectbox(
                "Screen zoom (display only — never saved)", options=ZOOM_OPTIONS,
                key="cs_zoom", label_visibility="collapsed",
            )

        _render_export_picture(
            workfile_state, base_chart_name, pop_layers,
            width_emu, height_emu, tweaks_str,
        )

        if st.button(
            "↺  Reset", type="primary", help="Reset — clear the Charts sheet back to a fresh state",
        ):
            _clear_sandbox_state()
            st.rerun()

    with right:
        _render_preview(
            workfile_state, base_chart_name, effective_shape_type, shape,
            pop_layers, target_rows, width_emu, height_emu, tweaks_str, zoom_choice,
        )
