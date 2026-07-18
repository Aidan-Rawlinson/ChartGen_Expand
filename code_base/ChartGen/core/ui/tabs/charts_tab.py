"""
charts_tab.py
Charts sheet — a sandbox for previewing and tuning chart rendering, wired as
a two-way sync with the Running Order.

Two entry points, always both available and always convertible into each
other:
  - Running Order row (bound mode) — loads an existing insert_chart row's
    chart-relevant fields; Overwrite defaults to that same row.
  - Data shape (free-play) — loads a cached dataset directly, with no row
    bound; save-back always requires picking a target row explicitly.

The Charts sheet owns this flow entirely — it reads a Running Order row and
writes back to it on explicit Save; the Running Order tab never pushes to,
or flags anything for, the Charts sheet.

Round-trip fields are a single maintainable list (CHART_SANDBOX_FIELDS,
running_order.schema) rather than hardcoded here, so extending the sync
later (e.g. a future shape-specific analytical field) means editing that
one list plus the small field_value_builders map below — not reworking this
tab's load/save logic.

Sizing (width_emu/height_emu) is never edited as raw EMU. The user-facing
unit is percent of the shorter dimension of the associated PowerPoint page
(core.shared.infrastructure.page_sizing) — this always applies, on both
entry paths, and always converts to EMU only at the point of writing back
to the Running Order.

Layout note: the left rail holds every control, grouped into expanders that
start collapsed except where there's a live reason to show them open
(Select Chart, and Select Visualisation while no chart type is chosen yet).
Zoom is the one expander whose control saves nothing to the Running Order —
it only changes how the already-correct preview looks on this screen — so
it sits last among the expanders, after Save to Running Order, rather than
grouped with the fields that do save. Reset sits at the very bottom of the
rail, below every other control, and only appears once a chart has actually
been selected (it lives after the early return on an unselected data shape,
so it's structurally absent until then rather than merely hidden).

Running Order rows are referenced here by row_id, not by list position or
by a descriptive label — row_id is stable across an Overwrite, so a
selection surviving a rerun always still means the same row. Only an Insert
(which shifts row_ids after the insertion point) invalidates it, which is
why sandbox state referencing rows is cleared after every save.
"""

from dataclasses import replace as _replace

import streamlit as st

from core.acquisition.toolkit_nhs.peer_groups import get_peer_group_value_options
from core.output_generation.definition.running_order import (
    get_valid_chart_refs_for_cache_file,
    build_populations_options, parse_populations_string, build_populations_string,
    parse_metric_periods_string, build_metric_periods_string,
    CHART_SANDBOX_FIELDS, overwrite_row_fields, insert_new_row,
)
from core.output_generation.execution.charts.base_charts import render_chart
from core.output_generation.execution.charts.chart_type_map import get_valid_chart_types
from core.shared.infrastructure.page_sizing import (
    percent_to_emu, emu_to_percent, get_page_size_emu,
    has_known_template_page_size, STANDARD_PAGE_SIZES_EMU, DEFAULT_STANDARD_PAGE_SIZE,
)
from core.shared.infrastructure.report_context import build_report_context
from core.shared.infrastructure.soft_parents import resolve_full_unit_set
from core.shared.normalisation_containers.population_layers import build_population_layers
from core.shared.normalisation_containers.shapes import apply_period_range
from core.shared.normalisation_containers.shape_transforms import maybe_convert_periods_to_metrics
from core.ui.common.guidance import render_tab_header
from core.workfile.state.session_state import settings, master_table, cached_files, manifest, load_shape_ps, ws

ZOOM_OPTIONS = ["0.75x", "Actual size (approximately)", "1.25x", "1.5x", "2x", "Fit to screen"]
ZOOM_MULTIPLIERS = {"0.75x": 0.75, "Actual size (approximately)": 1.0, "1.25x": 1.25, "1.5x": 1.5, "2x": 2.0}
DEFAULT_ZOOM = "Actual size (approximately)"
CS_KEY_PREFIX = "cs_"

# Placeholder option values, used as literal entries in each dropdown's own
# options list rather than Python None — None triggers Streamlit's own
# built-in "Choose an option" placeholder once pre-set into session_state,
# which fights with a custom format_func. A plain string sentinel avoids
# that ambiguity entirely and doubles as the box's display text when
# nothing is selected.
RO_PLACEHOLDER = "- Running order line -"
SHAPE_PLACEHOLDER = "- Chart list -"
TARGET_PLACEHOLDER = "- Select target row -"

# Sandbox state referencing a specific Running Order row by row_id — cleared
# after every save, since an Insert renumbers row_ids after the insertion
# point and an Overwrite changes the very fields a stale label would show.
ROW_REFERENCING_KEYS = [
    "cs_ro_choice", "cs_last_loaded_ro", "cs_bound_row_idx",
    "cs_bound_shape_type", "cs_target_row_choice",
]


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clear_sandbox_state():
    for k in list(st.session_state.keys()):
        if k.startswith(CS_KEY_PREFIX):
            del st.session_state[k]


def _clear_row_referencing_state():
    for k in ROW_REFERENCING_KEYS:
        st.session_state.pop(k, None)


def render_charts_tab():
    render_tab_header("Chart Review, Customisation and Formatting", "charts")

    the_cached_files = cached_files()
    the_manifest = manifest()

    if not the_cached_files:
        st.info("No cached chart data found. Use the Imports tab to fetch data first.")
        return

    workfile_state = ws()
    the_settings = settings()

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

    def ro_row_label(row_id):
        r = ro_rows[row_id_to_idx[row_id]]
        cache_label = label_by_cache_file.get(str(r.get("cache_file", "") or ""), r.get("cache_file", "") or "— no data —")
        ctype = str(r.get("chart_type_ref", "") or "— no chart type —")
        return f"Row {row_id}: {ctype} · {cache_label}"

    def format_row_choice(v):
        return v if v == RO_PLACEHOLDER else ro_row_label(v)

    def format_target_choice(v):
        return v if v == TARGET_PLACEHOLDER else ro_row_label(v)

    left, right = st.columns([1, 4.7])

    with left:
        # Defensive clamp — a row selected earlier may have been edited away
        # from insert_chart (or deleted) via the Running Order tab since.
        if st.session_state.get("cs_ro_choice") not in ([RO_PLACEHOLDER] + chart_row_ids):
            st.session_state["cs_ro_choice"] = RO_PLACEHOLDER

        reset_triggered = False

        with st.expander("Select Chart", expanded=True):
            ro_choice = st.selectbox(
                "Running Order row", options=[RO_PLACEHOLDER] + chart_row_ids,
                format_func=format_row_choice, key="cs_ro_choice",
                label_visibility="collapsed",
            )

            # --- Detect a new Running Order row selection and stage its
            #     fields for loading, before any affected widget below is
            #     rendered this run. Re-selecting the placeholder after a
            #     real row was loaded is treated as a full reset. ---
            last_loaded_ro = st.session_state.get("cs_last_loaded_ro", "__unset__")
            if ro_choice != last_loaded_ro:
                if ro_choice == RO_PLACEHOLDER and last_loaded_ro not in (RO_PLACEHOLDER, "__unset__"):
                    reset_triggered = True
                st.session_state["cs_last_loaded_ro"] = ro_choice
                if ro_choice == RO_PLACEHOLDER:
                    st.session_state.pop("cs_bound_row_idx", None)
                    st.session_state.pop("cs_bound_shape_type", None)
                else:
                    row_idx = row_id_to_idx[ro_choice]
                    row = ro_rows[row_idx]
                    cache_file = str(row.get("cache_file", "") or "")
                    shape_type = the_manifest.get(cache_file, {}).get("shape_type", "")
                    page_w, page_h = get_page_size_emu(the_settings, st.session_state.get("cs_manual_page_size"))
                    w_emu = _int_or_none(row.get("width_emu"))
                    h_emu = _int_or_none(row.get("height_emu"))

                    st.session_state["cs_bound_row_idx"] = row_idx
                    st.session_state["cs_bound_shape_type"] = shape_type
                    st.session_state["cs_pending_shape_choice"] = label_by_cache_file.get(cache_file)
                    st.session_state["cs_pending_chart_type_ref"] = str(row.get("chart_type_ref", "") or "")
                    st.session_state["cs_pending_populations_str"] = str(row.get("populations", "") or "")
                    st.session_state["cs_pending_start_period"] = str(row.get("start_period", "") or "")
                    st.session_state["cs_pending_end_period"] = str(row.get("end_period", "") or "")
                    st.session_state["cs_pending_metric_periods_str"] = str(row.get("metric_periods", "") or "")
                    st.session_state["cs_width_pct"] = round(emu_to_percent(w_emu, page_w, page_h), 1) if w_emu else 50.0
                    st.session_state["cs_height_pct"] = round(emu_to_percent(h_emu, page_w, page_h), 1) if h_emu else 50.0
                    st.session_state["cs_target_row_choice"] = ro_choice

            if "cs_pending_shape_choice" in st.session_state:
                pending_shape_label = st.session_state.pop("cs_pending_shape_choice")
                if pending_shape_label is not None:
                    st.session_state["cs_shape_choice"] = pending_shape_label
            st.session_state.setdefault("cs_shape_choice", SHAPE_PLACEHOLDER)

            shape_choice = st.selectbox(
                "Data shape", options=[SHAPE_PLACEHOLDER] + list(file_options.keys()),
                key="cs_shape_choice", label_visibility="collapsed",
            )

            # Re-selecting the placeholder after a real dataset was loaded is
            # also treated as a full reset.
            last_shape_choice = st.session_state.get("cs_last_shape_choice", "__unset__")
            if shape_choice != last_shape_choice:
                if shape_choice == SHAPE_PLACEHOLDER and last_shape_choice not in (SHAPE_PLACEHOLDER, "__unset__"):
                    reset_triggered = True
                st.session_state["cs_last_shape_choice"] = shape_choice

        if reset_triggered:
            _clear_sandbox_state()
            st.rerun()

        bound_row_idx = st.session_state.get("cs_bound_row_idx")

        if shape_choice == SHAPE_PLACEHOLDER:
            return

        selected_file = file_options[shape_choice]
        shape, shape_type = load_shape_ps(selected_file)

        # --- Shape mismatch warning — bound row still targeted, nothing blocked ---
        bound_shape_type = st.session_state.get("cs_bound_shape_type")
        if bound_row_idx is not None and bound_shape_type and bound_shape_type != shape_type:
            st.warning(
                "This data is a different shape than the bound Running Order row "
                f"('{bound_shape_type}' → '{shape_type}'). Chart type will need to be reselected."
            )

        # --- Period range and metric-periods conversion (TimeSeries only) —
        # both reshape `shape` ahead of the chart-type choice below, since
        # converting periods into metrics changes which chart types are
        # valid (NumericSeries's, not TimeSeries's). Options are built from
        # this shape's own period list so the user only ever picks a label,
        # never types an id. ---
        start_period = ""
        end_period = ""
        metric_period_ids = []
        converts_to_metrics = False
        if shape_type == "TimeSeries" and shape.periods:
            period_ids = [p.period_id for p in shape.periods]
            label_by_period_id = {p.period_id: p.period_label for p in shape.periods}

            if "cs_pending_start_period" in st.session_state:
                pending_start = st.session_state.pop("cs_pending_start_period")
                st.session_state["cs_start_period"] = pending_start if pending_start in period_ids else ""
            if "cs_pending_end_period" in st.session_state:
                pending_end = st.session_state.pop("cs_pending_end_period")
                st.session_state["cs_end_period"] = pending_end if pending_end in period_ids else ""
            st.session_state.setdefault("cs_start_period", "")
            st.session_state.setdefault("cs_end_period", "")
            # Clamp — a prior shape's periods may not include the current selection.
            if st.session_state["cs_start_period"] not in ([""] + period_ids):
                st.session_state["cs_start_period"] = ""
            if st.session_state["cs_end_period"] not in ([""] + period_ids):
                st.session_state["cs_end_period"] = ""

            def _period_format(v):
                return "(full range)" if v == "" else label_by_period_id.get(v, v)

            with st.expander("Period Range", expanded=False):
                st.caption("Start period")
                start_period = st.selectbox(
                    "Start period", options=[""] + period_ids, format_func=_period_format,
                    key="cs_start_period", label_visibility="collapsed",
                )
                st.caption("End period")
                end_period = st.selectbox(
                    "End period", options=[""] + period_ids, format_func=_period_format,
                    key="cs_end_period", label_visibility="collapsed",
                )
                if start_period and end_period and period_ids.index(start_period) > period_ids.index(end_period):
                    st.warning("Start period is after end period — this resolves to an empty range.")

            if start_period or end_period:
                shape = apply_period_range(shape, start_period, end_period)

            # --- Convert Periods to Metrics — a different concept from the
            # range above: one or more discrete periods, each becoming its
            # own output metric (one per source Metric-Series x selected
            # period), turning this into a NumericSeries snapshot. Options
            # reflect the range trim above, so a period already trimmed out
            # can't be picked here only to error later. ---
            period_ids_in_scope = [p.period_id for p in shape.periods]
            label_by_period_id_in_scope = {p.period_id: p.period_label for p in shape.periods}

            if "cs_pending_metric_periods_str" in st.session_state:
                pending_mp_str = st.session_state.pop("cs_pending_metric_periods_str")
                pending_mp_ids = parse_metric_periods_string(pending_mp_str)
                st.session_state["cs_metric_periods"] = [
                    pid for pid in pending_mp_ids if pid in period_ids_in_scope
                ]
            st.session_state.setdefault("cs_metric_periods", [])
            st.session_state["cs_metric_periods"] = [
                pid for pid in st.session_state["cs_metric_periods"] if pid in period_ids_in_scope
            ]

            with st.expander("Convert to Metrics", expanded=False):
                metric_period_ids = st.multiselect(
                    "Periods", options=period_ids_in_scope,
                    format_func=lambda v: label_by_period_id_in_scope.get(v, v),
                    key="cs_metric_periods", label_visibility="collapsed",
                )

            if metric_period_ids:
                try:
                    shape = maybe_convert_periods_to_metrics(shape, metric_period_ids)
                    converts_to_metrics = True
                except ValueError as e:
                    st.error(f"Metric-periods conversion failed: {e}")
                    metric_period_ids = []
        else:
            # Not TimeSeries, or no periods on this shape — clear any stale
            # selection so a later TimeSeries load doesn't inherit it.
            st.session_state.pop("cs_pending_start_period", None)
            st.session_state.pop("cs_pending_end_period", None)
            st.session_state.pop("cs_start_period", None)
            st.session_state.pop("cs_end_period", None)
            st.session_state.pop("cs_pending_metric_periods_str", None)
            st.session_state.pop("cs_metric_periods", None)

        metric_periods_str = build_metric_periods_string(metric_period_ids)

        # --- Chart type — filtered to this shape (or, if metric_periods
        # converted it, to NumericSeries instead), clamped before rendering ---
        effective_shape_type = "NumericSeries" if converts_to_metrics else shape_type
        valid_types = get_valid_chart_types(effective_shape_type)
        if not valid_types:
            st.warning(f"No Base Charts defined for shape type '{effective_shape_type}'.")
            return
        valid_refs = get_valid_chart_refs_for_cache_file(
            selected_file, the_manifest, converts_to_metrics=converts_to_metrics
        )
        type_desc_by_ref = {ref: desc for ref, desc in valid_types}

        if "cs_pending_chart_type_ref" in st.session_state:
            pending_ref = st.session_state.pop("cs_pending_chart_type_ref")
            st.session_state["cs_chart_type_ref"] = pending_ref if pending_ref in valid_refs else ""
        if st.session_state.get("cs_chart_type_ref", "") not in ([""] + valid_refs):
            st.session_state["cs_chart_type_ref"] = ""
        st.session_state.setdefault("cs_chart_type_ref", "")

        # Auto-expanded while no chart type is chosen yet; collapses itself
        # the moment one is picked (re-evaluated fresh each run).
        chart_settings_expanded = (st.session_state.get("cs_chart_type_ref", "") == "")
        with st.expander("Select Visualisation", expanded=chart_settings_expanded):
            chart_type_ref = st.selectbox(
                "Base chart", options=[""] + valid_refs,
                format_func=lambda v: "— select chart type —" if v == "" else type_desc_by_ref.get(v, v),
                key="cs_chart_type_ref", label_visibility="collapsed",
            )

        # --- Populations ---
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
        target_table = shape.population_table or master_table_name
        target_rows = workfile_state.tables.get(target_table, [])
        selected_ids = {r["unit_id"] for r in full_unit_set.get(target_table, [])}

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
                    "Width", min_value=1.0, max_value=200.0, step=1.0, format="%.1f",
                    key="cs_width_pct", label_visibility="collapsed",
                )
            with h_col:
                st.caption("Height")
                height_pct = st.number_input(
                    "Height", min_value=1.0, max_value=200.0, step=1.0, format="%.1f",
                    key="cs_height_pct", label_visibility="collapsed",
                )

        page_w, page_h = get_page_size_emu(the_settings, st.session_state.get("cs_manual_page_size"))
        width_emu = percent_to_emu(width_pct, page_w, page_h)
        height_emu = percent_to_emu(height_pct, page_w, page_h)

        # --- Save to Running Order ---
        target_default = ro_choice if ro_choice in chart_row_ids else TARGET_PLACEHOLDER
        current_target = st.session_state.get("cs_target_row_choice", target_default)
        if current_target not in chart_row_ids:
            current_target = TARGET_PLACEHOLDER
        st.session_state.setdefault("cs_target_row_choice", current_target)
        if st.session_state.get("cs_target_row_choice") not in ([TARGET_PLACEHOLDER] + chart_row_ids):
            st.session_state["cs_target_row_choice"] = TARGET_PLACEHOLDER

        with st.expander("Save to Running Order", expanded=False):
            st.session_state.setdefault("cs_action", "Overwrite selected row")
            st.caption("Action")
            action = st.selectbox(
                "Action",
                options=["Overwrite selected row", "Insert above selected row", "Insert below selected row"],
                key="cs_action", label_visibility="collapsed",
            )
            st.caption("Target Running Order row")
            target_choice = st.selectbox(
                "Target Running Order row", options=[TARGET_PLACEHOLDER] + chart_row_ids,
                format_func=format_target_choice, key="cs_target_row_choice",
                label_visibility="collapsed",
            )
            save_clicked = st.button("💾  Save to Running Order", type="primary", use_container_width=True)

        if save_clicked:
            if target_choice == TARGET_PLACEHOLDER:
                st.error("Select a target Running Order row first.")
            elif not chart_type_ref:
                st.error("Select a chart type before saving.")
            else:
                target_idx = row_id_to_idx[target_choice]
                field_value_builders = {
                    "chart_type_ref": lambda: chart_type_ref,
                    "cache_file":     lambda: selected_file,
                    "populations":    lambda: populations_str,
                    "start_period":   lambda: start_period,
                    "end_period":     lambda: end_period,
                    "metric_periods": lambda: metric_periods_str,
                    "width_emu":      lambda: width_emu,
                    "height_emu":     lambda: height_emu,
                }
                field_values = {f: field_value_builders[f]() for f in CHART_SANDBOX_FIELDS}

                if action == "Overwrite selected row":
                    overwrite_row_fields(workfile_state.running_order_rows, target_idx, field_values)
                elif action == "Insert above selected row":
                    insert_new_row(workfile_state.running_order_rows, target_idx, field_values, "above")
                else:
                    insert_new_row(workfile_state.running_order_rows, target_idx, field_values, "below")
                workfile_state.dirty = True
                # row_id references shift on Insert, and this row's own displayed
                # content just changed on Overwrite — clear rather than risk a
                # stale reference on the next rerun.
                _clear_row_referencing_state()
                st.success("Saved to Running Order.")
                st.rerun()

        with st.expander("Zoom", expanded=False):
            st.session_state.setdefault("cs_zoom", DEFAULT_ZOOM)
            zoom_choice = st.selectbox(
                "Screen zoom (display only — never saved)", options=ZOOM_OPTIONS,
                key="cs_zoom", label_visibility="collapsed",
            )

        if st.button(
            "↺  Reset", type="primary", help="Reset — clear the Charts sheet back to a fresh state",
        ):
            _clear_sandbox_state()
            st.rerun()

    with right:
        if not chart_type_ref:
            return

        try:
            pop_layers = build_population_layers(shape, preview_populations_str, target_rows, selected_ids)
        except Exception:
            pop_layers = []
        if not pop_layers:
            pop_layers = [_replace(shape, population_label="All")]

        with st.spinner("Rendering…"):
            image_bytes, autotable_stats = render_chart(
                chart_type_ref, pop_layers, width=width_pct, height=height_pct, report_context=rc
            )

        if zoom_choice == "Fit to screen":
            st.image(image_bytes, use_container_width=True)
        else:
            multiplier = ZOOM_MULTIPLIERS.get(zoom_choice, 1.0)
            px_width = max(50, int((width_emu / 914400) * 96 * multiplier))
            st.image(image_bytes, width=px_width)
            if zoom_choice == DEFAULT_ZOOM:
                st.caption(
                    "Sized to approximate true print size — actual on-screen size depends on "
                    "your monitor and OS display-scaling settings."
                )

        if autotable_stats:
            st.caption("Autotable statistics")
            st.json(autotable_stats)
