"""
preview.py
The right-hand column: the rendered chart itself, then the summary-stats
and unit-list tables.

Renders at CHART_RENDER_SCALE times the real target size and displays at
the real size via CSS, so the browser shrinks the image back down exactly
as PowerPoint does.

Stats and unit lists are read straight off the population layers, not
relayed back through the Base Chart function, which only ever produces
the image. Nothing is recalculated here.
"""

import streamlit as st

from chartgen.output_generation.execution.charts.custom_charts import (
    compile_custom_chart, get_chart_callable,
)
from chartgen.shared.infrastructure.render_scale import CHART_RENDER_SCALE
from chartgen.shared.infrastructure.value_formatting import format_reference_value
from chartgen.shared.normalisation_containers.shapes import (
    reference_rows_for_shape_type, summary_stats_by_layer, units_by_layer, unit_has_data,
)
from chartgen.ui.tabs.charts_tab.constants import ZOOM_MULTIPLIERS


def _svg_preview_html(svg_text, width_css):
    """
    Forces an SVG's rendered size to width_css (a CSS width value, e.g.
    "480px" or "100%") via an inline style on the SVG's own root element,
    since st.markdown has no width parameter the way st.image does. Used
    instead of st.image because st.image goes through PIL, which can't
    decode SVG, and every Base Chart returns SVG bytes. Field-for-field the
    same helper as output_tables_tab/chart_cells.py's own copy, deliberately
    not shared,
    matching the standalone-artefact convention for the rendering
    domains themselves.
    """
    styled = svg_text.replace("<svg ", '<svg style="width:100%;height:auto;display:block" ', 1)
    return f'<div style="width:{width_css}">{styled}</div>'




def _render_preview(workfile_state, base_chart_name, effective_shape_type, shape,
                    pop_layers, target_rows, width_emu, height_emu, tweaks_str, zoom_choice):
    """
    Render the preview image and the tables below it. Called from inside
    the right-hand column.
    """
    if not base_chart_name:
        return

    # A validated-but-not-yet-saved custom chart, staged in the Custom
    # Charts expander, takes over the preview for the base_chart_name it
    # was validated against only — switching to a different chart type
    # falls straight back to that chart's own resolved callable, rather
    # than carrying a stale override across.
    temp_code = st.session_state.get("cs_temp_custom_code")
    temp_for_chart = st.session_state.get("cs_temp_custom_for_chart")

    with st.spinner("Rendering…"):
        try:
            if temp_code and temp_for_chart == base_chart_name:
                chart_func = compile_custom_chart(temp_code)
            else:
                chart_func = get_chart_callable(base_chart_name, workfile_state.custom_chart_code)
            # Called at CHART_RENDER_SCALE times the real target size
            # -- see that constant's own comment -- then displayed
            # below at the real, unmultiplied px width, so the browser
            # shrinks it back down exactly as PowerPoint does.
            image_bytes = chart_func(
                pop_layers, width_emu=width_emu * CHART_RENDER_SCALE,
                height_emu=height_emu * CHART_RENDER_SCALE, tweaks=tweaks_str,
            )
        except Exception as e:
            st.error(f"Chart failed to render: {e}")
            return

    # Stats and unit lists are a property of the data shape, read
    # straight off pop_layers here — not relayed back through the Base
    # Chart function, which only ever produces the image.
    layer_summary_stats = summary_stats_by_layer(pop_layers)
    layer_units = units_by_layer(pop_layers)

    if zoom_choice == "Fit to screen":
        st.markdown(_svg_preview_html(image_bytes.read().decode("utf-8"), "100%"), unsafe_allow_html=True)
    else:
        multiplier = ZOOM_MULTIPLIERS.get(zoom_choice, 1.0)
        px_width = max(50, int((width_emu / 914400) * 96 * multiplier))
        st.markdown(
            _svg_preview_html(image_bytes.read().decode("utf-8"), f"{px_width}px"),
            unsafe_allow_html=True,
        )

    # --- Summary stats and unit lists — one summary-stats table per
    # (population layer x metric-series), then, in a separate labelled
    # section, one unit-list table per population layer (units belong
    # to the whole layer, not to an individual metric-series — every
    # metric-series in a shape instance shares the same population).
    # Both read what each layer's own shape instance already holds,
    # via summary_stats_by_layer and units_by_layer called directly
    # against pop_layers. Nothing is recalculated here, and the chart
    # function only ever produces the image.
    #
    # Reference ids are short and scoped to this shape type, so they can
    # eventually double as PowerPoint table replacement tags.
    #
    # "Name" is not on the shape's own unit records, which carry id and
    # code only. It is resolved from the population table already loaded
    # for this chart.
    # ---
    name_by_unit_id = {str(r.get("unit_id")): r.get("unit_name", "") for r in target_rows}

    if layer_summary_stats:
        st.caption("Summary stats")
        for layer_label, stats in layer_summary_stats.items():
            rows_by_series = reference_rows_for_shape_type(effective_shape_type, stats)
            for series_name, rows in rows_by_series.items():
                with st.expander(f"{layer_label} — {series_name}", expanded=False):
                    display_rows = [
                        {
                            "Reference": r["id"],
                            "Statistic": r["label"],
                            "Value": format_reference_value(r["value"], r["kind"], shape.format_modifier),
                        }
                        for r in rows
                    ]
                    st.table(display_rows)

    if layer_units:
        st.caption("Units included")
        for layer_label, units in layer_units.items():
            with st.expander(f"{layer_label} — Units", expanded=False):
                unit_rows = [
                    {
                        "ID": u.unit_id,
                        "Code": u.unit_code,
                        "Name": name_by_unit_id.get(str(u.unit_id), ""),
                        "Has Data": "Y" if unit_has_data(u) else "N",
                    }
                    for u in units
                ]
                if unit_rows:
                    st.table(unit_rows)
                else:
                    st.caption("No units in this population layer.")
