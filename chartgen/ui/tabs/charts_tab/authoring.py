"""
authoring.py
The Custom Charts round-trip (download a bundle, paste the result back,
validate, preview, save as a new chart) and Export Picture.

Two separate functions rather than one, because the Zoom control sits
between them in the left rail and widget order cannot change.

Both respect a validated-but-unsaved Custom Charts override the same way
the preview does, so what is exported always matches what is on screen.
"""

import os

import streamlit as st

from chartgen.output_generation.execution.charts.base_charts import CHART_REGISTRY
from chartgen.output_generation.execution.charts.custom_charts import (
    validate_custom_chart_code, compile_custom_chart, CustomChartError,
    get_chart_callable, build_bundle,
)
from chartgen.shared.infrastructure.cg_extracts import get_extracts_folder
from chartgen.shared.infrastructure.render_scale import CHART_RENDER_SCALE


def _render_custom_charts(workfile_state, base_chart_name, effective_shape_type,
                          pop_layers, width_emu, height_emu, tweaks_str):
    """Render the Custom Charts expander."""
    with st.expander("Custom Charts", expanded=False):
        st.caption(
            "Download a self-contained bundle for the chart currently selected, "
            "hand it to an AI to modify or replace, then paste the result back in "
            "to preview and, if you're happy with it, save as a new chart."
        )

        if not base_chart_name:
            st.caption("Select a chart type above first.")
        else:
            # width_emu/height_emu passed here at CHART_RENDER_SCALE
            # times the real target size -- the same inflated value
            # this chart is actually called with at runtime (see that
            # constant's own comment), so the bundle's own "Live data
            # for this chart, right now" section reports the true
            # figures an AI author needs to reason about, not the
            # row's own nominal target size.
            bundle_text = build_bundle(
                base_chart_name, effective_shape_type, pop_layers,
                width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE,
                tweaks_str, workfile_state.custom_chart_code,
            )
            st.download_button(
                "⬇  Download bundle for this chart", data=bundle_text,
                file_name=f"{base_chart_name}_custom_chart_bundle.md",
                mime="text/markdown", use_container_width=True,
            )

        st.session_state.setdefault("cs_custom_code_input", "")
        custom_code_input = st.text_area(
            "Paste updated chart code", key="cs_custom_code_input", height=200,
            help="Paste the complete function returned by the AI — one function, ready to run as-is.",
        )

        if st.button("Validate && Preview", use_container_width=True):
            try:
                validate_custom_chart_code(custom_code_input)
                st.session_state["cs_temp_custom_code"] = custom_code_input
                st.session_state["cs_temp_custom_for_chart"] = base_chart_name
                st.success("Valid — previewing below.")
            except CustomChartError as e:
                st.session_state.pop("cs_temp_custom_code", None)
                st.session_state.pop("cs_temp_custom_for_chart", None)
                st.error(str(e))

        temp_active = (
            st.session_state.get("cs_temp_custom_code")
            and st.session_state.get("cs_temp_custom_for_chart") == base_chart_name
        )
        if temp_active:
            st.caption("Save this as a new custom chart")
            save_name = st.text_input("New chart name", key="cs_custom_save_name",
                                      label_visibility="collapsed", placeholder="New chart name")
            if st.button("💾  Save as custom chart", use_container_width=True):
                name = save_name.strip()
                existing_custom_refs = {r["base_chart_name"] for r in workfile_state.custom_chart_rows}
                if not name:
                    st.error("Enter a name for the new chart.")
                elif name == "temp":
                    st.error("'temp' is reserved and can't be used as a chart name.")
                elif name in CHART_REGISTRY or name in existing_custom_refs:
                    st.error(f"'{name}' is already in use by another chart. Choose a different name.")
                else:
                    from datetime import datetime, timezone
                    workfile_state.custom_chart_rows.append({
                        "base_chart_name": name,
                        "shape_type": effective_shape_type,
                        "added_at": datetime.now(timezone.utc).isoformat(),
                        "notes": "",
                    })
                    workfile_state.custom_chart_code[name] = st.session_state["cs_temp_custom_code"]
                    workfile_state.dirty = True
                    st.session_state.pop("cs_temp_custom_code", None)
                    st.session_state.pop("cs_temp_custom_for_chart", None)
                    st.session_state.pop("cs_custom_code_input", None)
                    st.success(f"Saved as '{name}' — now available in Select Visualisation.")
                    st.rerun()



def _render_export_picture(workfile_state, base_chart_name, pop_layers,
                           width_emu, height_emu, tweaks_str):
    """Render the Export Picture control. Must stay below Zoom."""
    # --- Export Picture — writes the currently configured chart's own
    # SVG output (the same bytes the preview on the right renders) to
    # the ChartGen Exports folder. Re-runs the chart function rather
    # than reusing the right column's own image_bytes, since that
    # stream is consumed by the preview's .read() before this button
    # (in the left rail) would ever get a chance to read it — mirrors
    # how Save to Running Order/Chart Store already recompute their
    # own values rather than reach across columns. Respects a
    # validated-but-unsaved Custom Charts override the same way the
    # preview does, so what's exported always matches what's on screen.
    if not base_chart_name:
        st.caption("Select a chart type to enable Export Picture.")
    elif st.button("🖼  Export Picture", use_container_width=True, key="cs_export_picture_btn"):
        temp_code = st.session_state.get("cs_temp_custom_code")
        temp_for_chart = st.session_state.get("cs_temp_custom_for_chart")
        try:
            if temp_code and temp_for_chart == base_chart_name:
                export_chart_func = compile_custom_chart(temp_code)
            else:
                export_chart_func = get_chart_callable(base_chart_name, workfile_state.custom_chart_code)
            # Deliberately exported oversized, matching exactly what a
            # PPTX embeds. Not shrunk back for the standalone file.
            export_image_bytes = export_chart_func(
                pop_layers, width_emu=width_emu * CHART_RENDER_SCALE,
                height_emu=height_emu * CHART_RENDER_SCALE, tweaks=tweaks_str,
            )
            svg_text = export_image_bytes.read().decode("utf-8")
        except Exception as e:
            st.error(f"Chart failed to render: {e}")
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(
                get_extracts_folder(workfile_state.workfile_path), f"{base_chart_name}_{timestamp}.svg",
            )
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(svg_text)
            st.success(f"Exported to {export_path}")
