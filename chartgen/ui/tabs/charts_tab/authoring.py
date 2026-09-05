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
from datetime import datetime, timezone

import streamlit as st

from chartgen.output_generation.execution.charts.base_charts import CHART_REGISTRY
from chartgen.output_generation.execution.charts.custom_charts import (
    validate_custom_chart_code, compile_custom_chart, CustomChartError,
    get_chart_callable, build_bundle,
)
from chartgen.shared.infrastructure.cg_extracts import get_extracts_folder
from chartgen.shared.infrastructure.render_font import render_font
from chartgen.shared.infrastructure.render_scale import CHART_RENDER_SCALE
from chartgen.ui.common.flash import queue_flash


def _save_custom_chart(workfile_state, name, effective_shape_type):
    """
    Write the staged, already-validated code under `name` and clear the
    staging keys.

    An existing bespoke chart of that name keeps its own row, so its
    added_at and notes are left exactly as the person left them -- only the
    stored code changes. Its shape_type is re-asserted from the cut being
    previewed, since that is the shape the pasted code was written against.
    """
    for row in workfile_state.custom_chart_rows:
        if row["base_chart_name"] == name:
            row["shape_type"] = effective_shape_type
            break
    else:
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
    queue_flash(f"Saved as '{name}' — now available in Select Visualisation.")


@st.dialog("Overwrite this chart?")
def _confirm_overwrite_custom_chart(workfile_state, name, effective_shape_type):
    """
    Confirm replacing an existing bespoke chart's code. Only reachable for
    a name this workfile already owns; a built-in's name is refused before
    this point.

    st.dialog reruns only this function while the dialog is open, so the
    preview behind it is untouched until a choice is made. Either button
    calls st.rerun(), which is what closes the dialog.
    """
    st.write(f"A bespoke chart named **{name}** already exists in this workfile.")
    st.write(
        "Overwriting replaces its stored code with what you have just pasted. "
        "Every Running Order row and Chart Store entry using this name will "
        "render with the new code from now on."
    )
    st.caption("The change is held in the workfile and written to disk on your next Save.")
    cancel_col, overwrite_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", use_container_width=True, key="cs_overwrite_cancel_btn"):
            st.rerun()
    with overwrite_col:
        if st.button("Overwrite", type="primary", use_container_width=True, key="cs_overwrite_confirm_btn"):
            _save_custom_chart(workfile_state, name, effective_shape_type)
            st.rerun()


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
            #
            # data is a callable, which st.download_button registers for
            # deferred execution: the bundle is built when someone actually
            # downloads it, not on every rerun. The closure is rebuilt each
            # run and captures this run's values, so what downloads is what
            # is on screen.
            st.download_button(
                "⬇  Download bundle for this chart",
                data=lambda: build_bundle(
                    base_chart_name, effective_shape_type, pop_layers,
                    width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE,
                    tweaks_str, workfile_state.custom_chart_code,
                ),
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
                elif name in CHART_REGISTRY:
                    # A built-in belongs to the application, not to this
                    # workfile, so its name is refused outright rather than
                    # offered as something to overwrite.
                    st.error(f"'{name}' is a built-in chart. Choose a different name.")
                elif name in existing_custom_refs:
                    _confirm_overwrite_custom_chart(workfile_state, name, effective_shape_type)
                else:
                    _save_custom_chart(workfile_state, name, effective_shape_type)
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
            # Rendered under the workfile's own font too, so the exported
            # file matches the deck rather than the machine's defaults.
            with render_font(workfile_state.settings.get("default_font", "")):
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
