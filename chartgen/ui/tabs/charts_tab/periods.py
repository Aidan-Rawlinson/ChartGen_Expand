"""
periods.py
Period Range and Convert to Metrics, TimeSeries only. Both reshape the
chart's data ahead of the chart-type choice, since converting periods
into metrics changes which chart types are valid, which is why this runs
where it does rather than alongside the other controls.

Also builds the three composite strings that actually get written back to
a row on Save. A stored id that this shape cannot resolve keeps whatever
label it was already stored with, rather than being rebuilt label-less --
re-saving for an unrelated reason must not silently strip a label a
report's own period range has since moved past.
"""

import streamlit as st

from chartgen.output_generation.definition.running_order import (
    build_metric_periods_string, parse_metric_periods_string,
)
from chartgen.shared.infrastructure.period_ids import (
    build_period_display, extract_period_id, extract_period_label,
)
from chartgen.shared.normalisation_containers.shapes import apply_period_range


def _render_period_controls(shape, shape_type, bound_row_idx, ro_rows, chart_store_by_id):
    """
    Render the period controls and return
    (start_period, end_period, metric_periods_str,
     start_period_to_save, end_period_to_save, metric_periods_to_save).

    The first three are what this preview's own cut is resolved with; the
    last three are what a Save writes to the row.
    """
    # --- Period range and metric-periods conversion (TimeSeries only).
    # Both reshape `shape` ahead of the chart-type choice below, since
    # converting periods into metrics changes which chart types are
    # valid. Options come from this shape's own period list, so a label
    # is picked rather than an id typed.
    #
    # A bound row's stored values are used exactly as given, never
    # clamped against this shape's period list: the preview must call
    # prepare_chart_cut with the same values insert_chart would, or it
    # is not previewing the output. A stored id absent from this shape
    # is still added to the widget's option list, because Streamlit
    # cannot hold a value outside its own options; the value itself is
    # never altered. ---
    # --- The bound entity's stored period fields, raw, exactly as last
    # saved. Used below only as a fallback, so a stored composite string
    # is not rebuilt label-less just because this render's live shape
    # cannot resolve that id. Empty dict in free-play mode, which
    # correctly yields "" for every lookup. ---
    if bound_row_idx is not None:
        _orig_period_row = ro_rows[bound_row_idx]
    elif st.session_state.get("cs_bound_chart_store_id") in chart_store_by_id:
        _orig_period_row = chart_store_by_id[st.session_state["cs_bound_chart_store_id"]]
    else:
        _orig_period_row = {}
    _orig_start_period_raw = str(_orig_period_row.get("start_period", "") or "")
    _orig_start_period_id = extract_period_id(_orig_start_period_raw)
    _orig_end_period_raw = str(_orig_period_row.get("end_period", "") or "")
    _orig_end_period_id = extract_period_id(_orig_end_period_raw)
    _orig_metric_periods_raw = str(_orig_period_row.get("metric_periods", "") or "")
    _orig_raw_by_metric_period_id = {
        extract_period_id(tok): tok
        for tok in _orig_metric_periods_raw.split("^") if tok.strip()
    }

    start_period = ""
    end_period = ""
    metric_period_ids = []
    # These are what actually get written back to the row on Save --
    # see the composite-string-building comments below for how each
    # is built.
    start_period_to_save = ""
    end_period_to_save = ""
    metric_periods_to_save = ""
    if shape_type == "TimeSeries" and shape.periods:
        period_ids = [p.period_id for p in shape.periods]
        label_by_period_id = {p.period_id: p.period_label for p in shape.periods}

        if "cs_pending_start_period" in st.session_state:
            st.session_state["cs_start_period"] = st.session_state.pop("cs_pending_start_period")
        if "cs_pending_end_period" in st.session_state:
            st.session_state["cs_end_period"] = st.session_state.pop("cs_pending_end_period")
        st.session_state.setdefault("cs_start_period", "")
        st.session_state.setdefault("cs_end_period", "")

        start_period_options = [""] + period_ids
        if st.session_state["cs_start_period"] not in start_period_options:
            start_period_options.append(st.session_state["cs_start_period"])
        end_period_options = [""] + period_ids
        if st.session_state["cs_end_period"] not in end_period_options:
            end_period_options.append(st.session_state["cs_end_period"])

        def _period_format(v):
            if v == "":
                return "(full range)"
            # Prefer this shape's own live label; fall back to
            # whatever label this same id was already stored with
            # (rather than showing a bare number) if the live shape
            # doesn't currently recognise it -- display only, doesn't
            # affect what's actually saved below.
            return (
                label_by_period_id.get(v)
                or (extract_period_label(_orig_start_period_raw) if v == _orig_start_period_id else "")
                or (extract_period_label(_orig_end_period_raw) if v == _orig_end_period_id else "")
                or v
            )

        with st.expander("Period Range", expanded=False):
            st.caption("Start period")
            start_period = st.selectbox(
                "Start period", options=start_period_options, format_func=_period_format,
                key="cs_start_period", label_visibility="collapsed",
            )
            st.caption("End period")
            end_period = st.selectbox(
                "End period", options=end_period_options, format_func=_period_format,
                key="cs_end_period", label_visibility="collapsed",
            )
            if (start_period and end_period and start_period in period_ids and end_period in period_ids
                    and period_ids.index(start_period) > period_ids.index(end_period)):
                st.warning("Start period is after end period — this resolves to an empty range.")

        # The string actually saved is built here, at the one moment
        # a label is known with certainty (this widget's own live
        # shape.periods) — "period_label(period_id)" when a live
        # label resolves. If it doesn't (this id isn't among the live
        # shape's own periods) but the id is exactly what this entity
        # already had stored, the previously stored string is kept
        # completely unchanged rather than rebuilt without its label
        # -- re-saving for an unrelated reason (resizing, chart type)
        # must not silently strip a label a report's own period range
        # has since moved past. A genuinely new, unresolvable pick
        # falls back to the bare id, same as typing one by hand.
        start_period_to_save = (
            build_period_display(start_period, label_by_period_id.get(start_period, ""))
            if label_by_period_id.get(start_period) else
            (_orig_start_period_raw if start_period == _orig_start_period_id else start_period)
        )
        end_period_to_save = (
            build_period_display(end_period, label_by_period_id.get(end_period, ""))
            if label_by_period_id.get(end_period) else
            (_orig_end_period_raw if end_period == _orig_end_period_id else end_period)
        )

        # Widget-options-only trim — mirrors what prepare_chart_cut
        # will do to the real shape below (a cheap, pure, idempotent
        # operation); needed here only so the Convert-to-Metrics
        # multiselect offers the periods actually left in range, not
        # the full unrestricted list. A stale start_period/end_period
        # never raises here (filter_time_series_periods falls an
        # unmatched id back to that end of the period axis) — only
        # metric_periods itself can raise, below.
        _widget_scope_shape = shape
        if start_period or end_period:
            _widget_scope_shape = apply_period_range(shape, start_period, end_period)
        period_ids_in_scope = [p.period_id for p in _widget_scope_shape.periods]
        label_by_period_id_in_scope = {p.period_id: p.period_label for p in _widget_scope_shape.periods}

        if "cs_pending_metric_periods_str" in st.session_state:
            pending_mp_str = st.session_state.pop("cs_pending_metric_periods_str")
            st.session_state["cs_metric_periods"] = parse_metric_periods_string(pending_mp_str)
        st.session_state.setdefault("cs_metric_periods", [])

        metric_period_options = list(period_ids_in_scope)
        for pid in st.session_state["cs_metric_periods"]:
            if pid not in metric_period_options:
                metric_period_options.append(pid)

        with st.expander("Convert to Metrics", expanded=False):
            metric_period_ids = st.multiselect(
                "Periods", options=metric_period_options,
                format_func=lambda v: label_by_period_id_in_scope.get(v, v),
                key="cs_metric_periods", label_visibility="collapsed",
            )

        # Same "build with a live label when one resolves, otherwise
        # keep exactly what was already stored for that same id"
        # rule as start_period_to_save/end_period_to_save above — one
        # composite (or bare) token per selected id, same order,
        # '^'-joined to match metric_periods itself.
        metric_periods_to_save = "^".join(
            build_period_display(pid, label_by_period_id_in_scope.get(pid, ""))
            if label_by_period_id_in_scope.get(pid) else
            _orig_raw_by_metric_period_id.get(pid, pid)
            for pid in metric_period_ids
        )
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

    return (start_period, end_period, metric_periods_str,
            start_period_to_save, end_period_to_save, metric_periods_to_save)
