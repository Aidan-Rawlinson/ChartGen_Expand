"""
charts_tab.py
Charts tab — preview any cached chart data against any valid Base Chart.
"""

import streamlit as st

from core.shared.infrastructure.report_context import build_report_context
from core.shared.normalisation_containers.population_layers import build_population_layers
from core.output_generation.execution.charts.base_charts import render_chart
from core.output_generation.execution.charts.chart_type_map import get_valid_chart_types
from core.workfile.state.session_state import settings, units, cached_files, manifest, load_shape_ps


def render_charts_tab():
    st.header("Chart Preview")

    the_cached_files = cached_files()
    the_manifest = manifest()

    if not the_cached_files:
        st.info("No cached chart data found. Use the Imports tab to fetch data first.")
        return

    def file_label(f):
        entry = the_manifest.get(f, {})
        label = entry.get("label", "")
        return f"{f}  —  {label}" if label else f

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

        units_local = units()
        rc = build_report_context(settings(), units_local)
        if rc:
            st.caption(f"Highlighting: **{rc.unit_code}** — {rc.unit_name}")

        default_pop = "All^Selected"
        try:
            pop_layers = build_population_layers(shape, default_pop, units_local, rc)
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
