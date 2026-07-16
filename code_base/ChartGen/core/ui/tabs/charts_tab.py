"""
charts_tab.py
Charts tab — preview any cached chart data against any valid Base Chart.
Resolves populations the same way a real batch run would: against whichever
table the previewed chart's own data belongs to (population_table), not
necessarily the master table.
"""

import streamlit as st

from core.shared.infrastructure.report_context import build_report_context
from core.shared.infrastructure.soft_parents import resolve_full_unit_set
from core.shared.normalisation_containers.population_layers import build_population_layers
from core.output_generation.execution.charts.base_charts import render_chart
from core.output_generation.execution.charts.chart_type_map import get_valid_chart_types
from core.workfile.state.session_state import settings, master_table, cached_files, manifest, load_shape_ps, ws


def render_charts_tab():
    st.header("Chart Preview")

    the_cached_files = cached_files()
    the_manifest = manifest()

    if not the_cached_files:
        st.info("No cached chart data found. Use the Imports tab to fetch data first.")
        return

    def file_label(f):
        entry = the_manifest.get(f, {})
        title = str(entry.get("chart_title", "")).strip()
        ref = str(entry.get("chart_ref", "")).strip()
        if title and title != "...":
            return f"{ref or f}  —  {title}"
        return ref or f

    file_options = {file_label(f): f for f in the_cached_files}
    selected_label = st.selectbox("Select a cached dataset", options=list(file_options.keys()), index=0)
    selected_file = file_options[selected_label]

    shape, shape_type = load_shape_ps(selected_file)
    valid_types = get_valid_chart_types(shape_type)
    st.caption(f"Shape type: **{shape_type}**")

    if not valid_types:
        st.warning(f"No Base Charts defined for shape type '{shape_type}'.")
        return

    type_options = {desc: ref for ref, desc in valid_types}
    selected_desc = st.selectbox(
        "Select a Base Chart", options=list(type_options.keys()),
        index=None, placeholder="Choose a chart type to render…",
    )

    if selected_desc:
        chart_ref = type_options[selected_desc]
        from dataclasses import replace as _replace

        units_local = master_table()
        rc = build_report_context(settings(), units_local)
        if rc:
            st.caption(f"Highlighting: **{rc.unit_code}** — {rc.unit_name}")

        workfile_state = ws()
        master_table_name = workfile_state.table_order[0] if workfile_state.table_order else ""
        reporting_row = (
            next((r for r in units_local if str(r["unit_id"]) == rc.unit_id), None) if rc else None
        )
        full_unit_set = (
            resolve_full_unit_set(reporting_row, master_table_name, workfile_state.tables)
            if reporting_row is not None else {}
        )

        target_table = shape.population_table or master_table_name
        target_rows = workfile_state.tables.get(target_table, [])
        selected_ids = {r["unit_id"] for r in full_unit_set.get(target_table, [])}

        # Bodge: pick up whatever set_default_populations actually has on the
        # Running Order, rather than hardcoding a guess — first matching row
        # wins, falls back to "All^Selected" if none exists yet.
        default_pop = "All^Selected"
        for ro_row in workfile_state.running_order_rows:
            if str(ro_row.get("function", "")).strip() == "set_default_populations":
                ro_pop = str(ro_row.get("populations", "") or "").strip()
                if ro_pop:
                    default_pop = ro_pop
                break

        try:
            pop_layers = build_population_layers(shape, default_pop, target_rows, selected_ids)
        except Exception:
            pop_layers = []
        if not pop_layers:
            pop_layers = [_replace(shape, population_label="All")]

        with st.spinner("Rendering…"):
            image_bytes, autotable_stats = render_chart(
                chart_ref, pop_layers, width=80, height=50, report_context=rc
            )
        st.image(image_bytes, use_container_width=True)

        if autotable_stats:
            st.caption("Autotable statistics")
            st.json(autotable_stats)
