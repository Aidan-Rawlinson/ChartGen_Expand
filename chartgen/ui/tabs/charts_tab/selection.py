"""
selection.py
The "Select Chart" box: the two entry points into the sandbox -- a
Running Order row (bound mode) and a Chart Store line -- plus the Data
shape picker and the Show Chart Store toggle.

Order inside this function is load-bearing and must not be rearranged.
Streamlit cannot retroactively change a widget already instantiated this
pass, so each entry point stages its values into "pending" keys before
the widgets those values target are created. Chart Store line in
particular MUST stay above Data shape; the comments below say so at each
point it matters.
"""

import streamlit as st

from chartgen.shared.infrastructure.page_sizing import emu_to_percent, get_page_size_emu
from chartgen.shared.infrastructure.period_ids import extract_metric_period_ids, extract_period_id
from chartgen.ui.tabs.charts_tab.constants import (
    CHART_STORE_PLACEHOLDER, CHART_STORE_TARGET_PLACEHOLDER, RO_PLACEHOLDER, SHAPE_PLACEHOLDER,
)
from chartgen.ui.tabs.charts_tab.helpers import _int_or_none
from chartgen.ui.tabs.charts_tab.state import (
    _clear_chart_store_referencing_state, _clear_row_referencing_state, _clear_sandbox_state,
)


def _render_select_chart(the_settings, the_manifest, ro_rows, row_id_to_idx, chart_row_ids,
                         chart_store_by_id, chart_store_ids, file_options, label_by_cache_file,
                         format_row_choice, format_chart_store_choice):
    """
    Render the Select Chart box and return (ro_choice, shape_choice).

    Called from inside the left-hand column, and expected to be the first
    thing rendered there -- see this module's own docstring on why the
    order cannot move.
    """
    # Defensive clamp — a row selected earlier may have been edited away
    # from insert_chart (or deleted) via the Running Order tab since.
    if st.session_state.get("cs_ro_choice") not in ([RO_PLACEHOLDER] + chart_row_ids):
        st.session_state["cs_ro_choice"] = RO_PLACEHOLDER

    # Applied here, before the "Chart Store line"/"Target Chart Store
    # entry" selectboxes below are created — staged the same way
    # "ot_pending_ro_choice_after_save" is (Output Tables tab): those
    # widgets have already been instantiated once this run wherever a
    # prior Save to Chart Store happened, so they can only be set to a
    # new value before their next instantiation.
    if "cs_pending_chart_store_choice_after_save" in st.session_state:
        pending_cstore = st.session_state.pop("cs_pending_chart_store_choice_after_save")
        if pending_cstore in chart_store_ids:
            st.session_state["cs_chart_store_choice"] = pending_cstore
            # Also sync "last loaded" so the Chart Store line detection
            # block below sees this as unchanged, not a fresh
            # selection — a save doesn't need the sandbox reloaded
            # from what it just wrote; recomputing Sizing (and
            # everything else) from EMU a second time here was the
            # source of the sandbox occasionally going stale after a
            # save, not a genuine new load.
            st.session_state["cs_last_loaded_chart_store"] = pending_cstore
    if "cs_pending_chart_store_target_after_save" in st.session_state:
        pending_cstore_target = st.session_state.pop("cs_pending_chart_store_target_after_save")
        if pending_cstore_target in chart_store_ids:
            st.session_state["cs_chart_store_target_choice"] = pending_cstore_target

    if st.session_state.get("cs_chart_store_choice") not in ([CHART_STORE_PLACEHOLDER] + chart_store_ids):
        st.session_state["cs_chart_store_choice"] = CHART_STORE_PLACEHOLDER
    if st.session_state.get("cs_chart_store_target_choice") not in (
        [CHART_STORE_TARGET_PLACEHOLDER] + chart_store_ids
    ):
        st.session_state["cs_chart_store_target_choice"] = CHART_STORE_TARGET_PLACEHOLDER

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
                st.session_state["cs_pending_base_chart_name"] = str(row.get("base_chart_name", "") or "")
                st.session_state["cs_pending_populations_str"] = str(row.get("populations", "") or "")
                # Widget state needs the bare period_id (it matches
                # options against the live shape's own period_ids);
                # the row's own stored value may carry a display label
                # too ("July 2025(1338)") -- extracted here for the
                # widget only, never rewritten back onto the row
                # itself (see schema.py's own note on why).
                st.session_state["cs_pending_start_period"] = extract_period_id(row.get("start_period", ""))
                st.session_state["cs_pending_end_period"] = extract_period_id(row.get("end_period", ""))
                st.session_state["cs_pending_metric_periods_str"] = extract_metric_period_ids(row.get("metric_periods", ""))
                st.session_state["cs_pending_tweaks_str"] = str(row.get("tweaks", "") or "")
                # The computed percentage is shown as it is, however
                # small. A tiny value means the row's stored EMU really
                # is tiny relative to the page, and that is what the
                # widget should say.
                st.session_state["cs_width_pct"] = round(emu_to_percent(w_emu, page_w, page_h), 2) if w_emu else 0.0
                st.session_state["cs_height_pct"] = round(emu_to_percent(h_emu, page_w, page_h), 2) if h_emu else 0.0
                st.session_state["cs_target_row_choice"] = ro_choice

                # Mutually exclusive with Chart Store line — this
                # widget hasn't rendered yet this run, so clearing its
                # own bookkeeping here (before it does) is enough; no
                # rerun needed, unlike the reverse direction below.
                _clear_chart_store_referencing_state()

        # --- Chart Store line: a second entry point into the same
        # sandbox fields, alongside Running Order row.
        #
        # MUST stay above "Data shape". Its pending values have to be
        # staged before the shared pending-value consumption step below
        # and before the Data shape selectbox is created. A widget
        # already instantiated this pass cannot be changed
        # retroactively, so moving this later needs an explicit rerun.
        #
        # A Chart Store entry has no position, so its Save-back offers
        # Add and Overwrite only, never Insert above or below. ---
        chart_store_choice = st.selectbox(
            "Chart Store line", options=[CHART_STORE_PLACEHOLDER] + chart_store_ids,
            format_func=format_chart_store_choice, key="cs_chart_store_choice",
            label_visibility="collapsed",
        )

        last_loaded_cstore = st.session_state.get("cs_last_loaded_chart_store", "__unset__")
        if chart_store_choice != last_loaded_cstore:
            if chart_store_choice == CHART_STORE_PLACEHOLDER and last_loaded_cstore not in (CHART_STORE_PLACEHOLDER, "__unset__"):
                reset_triggered = True
            st.session_state["cs_last_loaded_chart_store"] = chart_store_choice
            if chart_store_choice == CHART_STORE_PLACEHOLDER:
                st.session_state.pop("cs_bound_chart_store_id", None)
            else:
                cstore_row = chart_store_by_id[chart_store_choice]
                cstore_cache_file = str(cstore_row.get("cache_file", "") or "")
                cstore_page_w, cstore_page_h = get_page_size_emu(
                    the_settings, st.session_state.get("cs_manual_page_size")
                )
                cstore_w_emu = _int_or_none(cstore_row.get("width_emu"))
                cstore_h_emu = _int_or_none(cstore_row.get("height_emu"))

                st.session_state["cs_bound_chart_store_id"] = chart_store_choice
                st.session_state["cs_pending_shape_choice"] = label_by_cache_file.get(cstore_cache_file)
                st.session_state["cs_pending_base_chart_name"] = str(cstore_row.get("base_chart_name", "") or "")
                st.session_state["cs_pending_populations_str"] = str(cstore_row.get("populations", "") or "")
                st.session_state["cs_pending_start_period"] = extract_period_id(cstore_row.get("start_period", ""))
                st.session_state["cs_pending_end_period"] = extract_period_id(cstore_row.get("end_period", ""))
                st.session_state["cs_pending_metric_periods_str"] = extract_metric_period_ids(cstore_row.get("metric_periods", ""))
                st.session_state["cs_pending_tweaks_str"] = str(cstore_row.get("tweaks", "") or "")
                # Same near-zero-percentage guard as the Running Order
                # row-load path above — see that comment for why this
                # matters (output_tables_tab/sheet.py's row-load path already
                # has the equivalent guard; this was the one load path
                # here that didn't).
                st.session_state["cs_width_pct"] = (
                    round(emu_to_percent(cstore_w_emu, cstore_page_w, cstore_page_h), 2) if cstore_w_emu else 0.0
                )
                st.session_state["cs_height_pct"] = (
                    round(emu_to_percent(cstore_h_emu, cstore_page_w, cstore_page_h), 2) if cstore_h_emu else 0.0
                )
                st.session_state["cs_chart_store_target_choice"] = chart_store_choice
                st.session_state["cs_chart_store_action"] = "Overwrite selected entry"
                st.session_state["cs_chart_store_description"] = str(cstore_row.get("description", "") or "")

                # Mutually exclusive with Running Order row — but that
                # selectbox already rendered earlier this same run
                # (it's above this block), so clearing its bookkeeping
                # now only takes visual effect next pass; force it
                # rather than leaving the Running Order row box showing
                # a stale selection that no longer reflects what's
                # actually bound.
                _clear_row_referencing_state()
                st.rerun()

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

        # "Show Chart Store" sits last in the box, after every entry
        # point — it doesn't load anything into the sandbox itself, so
        # it has no ordering dependency the way Chart Store line does.
        show_chart_store_clicked = st.button(
            "🗂  Hide Chart Store" if st.session_state.get("cs_show_chart_store", False) else "🗂  Show Chart Store",
            use_container_width=True, key="cs_show_chart_store_btn",
        )
        if show_chart_store_clicked:
            st.session_state["cs_show_chart_store"] = not st.session_state.get("cs_show_chart_store", False)

    if reset_triggered:
        _clear_sandbox_state()
        st.rerun()

    return ro_choice, shape_choice
