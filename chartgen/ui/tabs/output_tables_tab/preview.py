"""
preview.py
Preview mode: table type, tweaks, sizing in percent, save-back to the
Running Order, the Custom Tables round-trip, zoom, and the rendered
image itself.

Mirrors the Charts sheet's own Preview mechanics wherever the concepts
match. Reset here clears Preview's own configuration only, never the
table selection, which lives in the shared box above.
"""

from datetime import datetime, timezone

import streamlit as st

from chartgen.output_generation.definition.running_order import (
    TABLE_SANDBOX_FIELDS, overwrite_row_fields, insert_new_row,
)
from chartgen.output_generation.execution.tables.base_tables import TABLE_REGISTRY
from chartgen.output_generation.execution.tables.custom_tables.bundle import build_bundle
from chartgen.output_generation.execution.tables.custom_tables.gate import (
    validate_custom_table_code, compile_custom_table, CustomTableError,
)
from chartgen.output_generation.execution.tables.custom_tables.resolve import (
    get_table_callable, custom_table_descriptions, all_table_type_refs,
)
from chartgen.output_generation.execution.tables.resolve import resolve_output_table
from chartgen.shared.infrastructure.page_sizing import (
    percent_to_emu, get_page_size_emu,
    has_known_template_page_size, STANDARD_PAGE_SIZES_EMU, DEFAULT_STANDARD_PAGE_SIZE,
)
from chartgen.shared.infrastructure.render_font import render_font
from chartgen.shared.infrastructure.render_scale import CHART_RENDER_SCALE
from chartgen.shared.infrastructure.report_context import build_report_context
from chartgen.shared.infrastructure.soft_parents import resolve_full_unit_set
from chartgen.ui.common.flash import queue_flash
from chartgen.ui.common.render_memo import render_signature, remember_render
from chartgen.ui.tabs.output_tables_tab.chart_cells import (
    _svg_preview_html, _splice_chart_cells_into_svg,
)
from chartgen.ui.tabs.output_tables_tab.constants import (
    TARGET_PLACEHOLDER, ZOOM_OPTIONS, ZOOM_MULTIPLIERS, DEFAULT_ZOOM,
)
from chartgen.ui.tabs.output_tables_tab.state import _clear_sandbox_state
from chartgen.workfile.state.session_state import master_table


def _current_full_unit_set(workfile_state, the_settings):
    units = master_table()
    rc = build_report_context(the_settings, units)
    master_table_name = workfile_state.table_order[0] if workfile_state.table_order else ""
    reporting_row = (
        next((r for r in units if str(r["unit_id"]) == rc.unit_id), None) if rc else None
    )
    return (
        resolve_full_unit_set(reporting_row, master_table_name, workfile_state.tables)
        if reporting_row is not None else {}
    )


def _save_custom_table(workfile_state, name):
    """
    Write the staged, already-validated code under `name` and clear the
    staging keys.

    An existing bespoke table of that name keeps its own row, so its
    added_at and notes are left exactly as the person left them -- only the
    stored code changes. A new name gets a new row.
    """
    existing_custom_refs = {r["table_type_ref"] for r in workfile_state.custom_table_rows}
    if name not in existing_custom_refs:
        workfile_state.custom_table_rows.append({
            "table_type_ref": name,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "notes": "",
        })
    workfile_state.custom_table_code[name] = st.session_state["ots_temp_custom_code"]
    workfile_state.dirty = True
    st.session_state.pop("ots_temp_custom_code", None)
    st.session_state.pop("ots_temp_custom_for_table", None)
    st.session_state.pop("ots_custom_code_input", None)
    queue_flash(f"Saved as '{name}' — now available in Select Visualisation.")


@st.dialog("Overwrite this table?")
def _confirm_overwrite_custom_table(workfile_state, name):
    """
    Confirm replacing an existing bespoke table's code. Only reachable for
    a name this workfile already owns; a built-in's name is refused before
    this point.

    st.dialog reruns only this function while the dialog is open, so the
    preview behind it is untouched until a choice is made. Either button
    calls st.rerun(), which is what closes the dialog.
    """
    st.write(f"A bespoke table named **{name}** already exists in this workfile.")
    st.write(
        "Overwriting replaces its stored code with what you have just pasted. "
        "Every Running Order row and Output Table using this name will render "
        "with the new code from now on."
    )
    st.caption("The change is held in the workfile and written to disk on your next Save.")
    cancel_col, overwrite_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", use_container_width=True, key="ots_overwrite_cancel_btn"):
            st.rerun()
    with overwrite_col:
        if st.button("Overwrite", type="primary", use_container_width=True, key="ots_overwrite_confirm_btn"):
            _save_custom_table(workfile_state, name)
            st.rerun()


# ---------------------------------------------------------------------------
# Preview mode -- acts on the table selected in the shared box above
# ---------------------------------------------------------------------------

def _render_preview_sandbox(workfile_state, the_settings, table_id, grid_rows,
                            table_row_ids, row_id_to_idx, id_to_name, ro_rows,
                            bound_ro_choice, format_row_choice):
    def format_target_choice(v):
        return v if v == TARGET_PLACEHOLDER else format_row_choice(v)

    left, right = st.columns([1, 4.7])
    table_type_ref = ""

    with left:
        custom_table_rows = workfile_state.custom_table_rows
        valid_refs = all_table_type_refs(custom_table_rows)
        type_desc_by_ref = {"plain_grid": "plain_grid"}
        for ref, desc in custom_table_descriptions(custom_table_rows):
            type_desc_by_ref[ref] = desc

        if "ots_pending_table_type_ref" in st.session_state:
            pending_ref = st.session_state.pop("ots_pending_table_type_ref")
            st.session_state["ots_table_type_ref"] = pending_ref if pending_ref in valid_refs else "plain_grid"
        st.session_state.setdefault("ots_table_type_ref", "plain_grid")
        if st.session_state["ots_table_type_ref"] not in valid_refs:
            st.session_state["ots_table_type_ref"] = "plain_grid"

        with st.expander("Select Visualisation", expanded=False):
            table_type_ref = st.selectbox(
                "Base table", options=valid_refs,
                format_func=lambda v: type_desc_by_ref.get(v, v),
                key="ots_table_type_ref", label_visibility="collapsed",
            )

        if "ots_pending_tweaks_str" in st.session_state:
            st.session_state["ots_tweaks_str"] = st.session_state.pop("ots_pending_tweaks_str")
        st.session_state.setdefault("ots_tweaks_str", "")

        with st.expander("Tweaks", expanded=False):
            tweaks_str = st.text_area(
                "Tweaks", key="ots_tweaks_str", label_visibility="collapsed",
                help="Free text passed straight through to the Base Table function's tweaks parameter.",
            )

        with st.expander("Sizing", expanded=False):
            if not has_known_template_page_size(the_settings):
                page_size_options = list(STANDARD_PAGE_SIZES_EMU.keys())
                st.session_state.setdefault("ots_manual_page_size", DEFAULT_STANDARD_PAGE_SIZE)
                st.caption("Page size")
                st.selectbox(
                    "Page size", options=page_size_options, key="ots_manual_page_size",
                    label_visibility="collapsed",
                )
            st.session_state.setdefault("ots_width_pct", 50.0)
            st.session_state.setdefault("ots_height_pct", 50.0)
            w_col, h_col = st.columns(2)
            with w_col:
                st.caption("Width")
                width_pct = st.number_input(
                    "Width", min_value=0.0, step=1.0, format="%.2f",
                    key="ots_width_pct", label_visibility="collapsed",
                )
            with h_col:
                st.caption("Height")
                height_pct = st.number_input(
                    "Height", min_value=0.0, step=1.0, format="%.2f",
                    key="ots_height_pct", label_visibility="collapsed",
                )

        page_w, page_h = get_page_size_emu(the_settings, st.session_state.get("ots_manual_page_size"))
        width_emu = percent_to_emu(width_pct, page_w, page_h)
        height_emu = percent_to_emu(height_pct, page_w, page_h)

        full_unit_set = _current_full_unit_set(workfile_state, the_settings)
        rc = build_report_context(the_settings, master_table())
        resolved = resolve_output_table(grid_rows, workfile_state, full_unit_set, rc)

        target_default = bound_ro_choice if bound_ro_choice in table_row_ids else TARGET_PLACEHOLDER
        current_target = st.session_state.get("ots_target_row_choice", target_default)
        if current_target not in table_row_ids:
            current_target = TARGET_PLACEHOLDER
        st.session_state.setdefault("ots_target_row_choice", current_target)
        if st.session_state.get("ots_target_row_choice") not in ([TARGET_PLACEHOLDER] + table_row_ids):
            st.session_state["ots_target_row_choice"] = TARGET_PLACEHOLDER

        # Applied here, before the "Target Running Order row" selectbox
        # below is created -- staged the same way "ot_ro_choice" is (see
        # Save to Running Order's success branch): that widget has already
        # rendered once this run wherever a prior save happened, so it can
        # only be set to a new value before its next instantiation.
        if "ots_pending_target_row_choice_after_save" in st.session_state:
            pending_target = st.session_state.pop("ots_pending_target_row_choice_after_save")
            if pending_target in table_row_ids:
                st.session_state["ots_target_row_choice"] = pending_target

        with st.expander("Save to Running Order", expanded=False):
            st.session_state.setdefault("ots_action", "Overwrite selected row")
            st.caption("Action")
            action = st.selectbox(
                "Action",
                options=["Overwrite selected row", "Insert above selected row", "Insert below selected row"],
                key="ots_action", label_visibility="collapsed",
            )
            st.caption("Target Running Order row")
            target_choice = st.selectbox(
                "Target Running Order row", options=[TARGET_PLACEHOLDER] + table_row_ids,
                format_func=format_target_choice, key="ots_target_row_choice",
                label_visibility="collapsed",
            )
            save_clicked = st.button(
                "\U0001F4BE  Save to Running Order", type="primary", use_container_width=True,
                key="ots_save_to_ro_btn",
            )

        if save_clicked:
            if target_choice == TARGET_PLACEHOLDER:
                st.error("Select a target Running Order row first.")
            elif not table_type_ref:
                st.error("Select a table type before saving.")
            else:
                target_idx = row_id_to_idx[target_choice]
                field_value_builders = {
                    "table_id":       lambda: table_id,
                    "table_type_ref": lambda: table_type_ref,
                    "width_emu":      lambda: width_emu,
                    "height_emu":     lambda: height_emu,
                    "tweaks":         lambda: tweaks_str,
                }
                field_values = {f: field_value_builders[f]() for f in TABLE_SANDBOX_FIELDS}

                if action == "Overwrite selected row":
                    overwrite_row_fields(workfile_state.running_order_rows, target_idx, field_values)
                    new_bound_row_id = target_choice  # row_id is unchanged by an Overwrite
                elif action == "Insert above selected row":
                    new_idx = insert_new_row(workfile_state.running_order_rows, target_idx, field_values, "above")
                    new_bound_row_id = workfile_state.running_order_rows[new_idx]["row_id"]
                else:
                    new_idx = insert_new_row(workfile_state.running_order_rows, target_idx, field_values, "below")
                    new_bound_row_id = workfile_state.running_order_rows[new_idx]["row_id"]
                workfile_state.dirty = True
                # Keep the row bound rather than clearing the selection. For
                # an Insert, the newly created row is the one now holding what
                # was saved, so that is the one that becomes bound.
                #
                # "ot_ro_choice" is widget-bound and already instantiated
                # earlier this run, so writing to it directly raises
                # StreamlitAPIException. Staged in a plain pending key
                # instead, applied at the top of render_output_tables_tab
                # before that selectbox is created on the next run.
                st.session_state["ot_pending_ro_choice_after_save"] = new_bound_row_id
                st.session_state.pop("ot_last_loaded_ro", None)
                st.session_state.pop("ot_bound_row_idx", None)
                st.session_state["ots_pending_target_row_choice_after_save"] = new_bound_row_id
                queue_flash("Saved to Running Order.")
                st.rerun()

        with st.expander("Custom Tables", expanded=False):
            st.caption(
                "Download a self-contained bundle for the table currently selected, "
                "hand it to an AI to modify or replace, then paste the result back in "
                "to preview and, if you're happy with it, save as a new table type."
            )

            st.session_state.setdefault("ots_bundle_include_charts", False)
            include_charts = st.checkbox(
                "Tick here to export charts", key="ots_bundle_include_charts",
                help="Also include full detail (settings, source code, and live data) for "
                     "every Chart Store entry referenced by a {Cn} marker in this table -- "
                     "off by default, since most table edits don't touch what's inside an "
                     "embedded chart, and resolving each one's live data has a real cost.",
            )
            full_unit_set_for_bundle = full_unit_set if include_charts else None

            # width_emu/height_emu passed here at CHART_RENDER_SCALE times
            # the real target size -- the same inflated value this table
            # is actually called with at runtime (see that constant's own
            # comment), so the bundle's own "Live data for this table,
            # right now" section reports the true figures an AI author
            # needs to reason about.
            #
            # data is a callable, which st.download_button registers for
            # deferred execution: the bundle is built when someone actually
            # downloads it, not on every rerun. With include_charts on that
            # matters a lot, since building it resolves live data for every
            # embedded chart. The closure is rebuilt each run and captures
            # this run's values, so what downloads is what is on screen.
            st.download_button(
                "\u2b07  Download bundle for this table",
                data=lambda: build_bundle(
                    table_type_ref, resolved["content"], resolved["column_widths"], resolved["row_heights"],
                    width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE, tweaks_str,
                    workfile_state.custom_table_code,
                    include_charts=include_charts, workfile_state=workfile_state,
                    full_unit_set=full_unit_set_for_bundle,
                ),
                file_name=f"{table_type_ref}_custom_table_bundle.md",
                mime="text/markdown", use_container_width=True,
                key=f"ots_download_bundle_{table_type_ref}",
            )

            st.session_state.setdefault("ots_custom_code_input", "")
            custom_code_input = st.text_area(
                "Paste updated table code", key="ots_custom_code_input", height=200,
                help="Paste the complete function returned by the AI — one function, ready to run as-is.",
            )

            if st.button("Validate && Preview", use_container_width=True, key="ots_validate_btn"):
                try:
                    validate_custom_table_code(custom_code_input)
                    st.session_state["ots_temp_custom_code"] = custom_code_input
                    st.session_state["ots_temp_custom_for_table"] = table_type_ref
                    st.success("Valid — previewing below.")
                except CustomTableError as e:
                    st.session_state.pop("ots_temp_custom_code", None)
                    st.session_state.pop("ots_temp_custom_for_table", None)
                    st.error(str(e))

            temp_active = (
                st.session_state.get("ots_temp_custom_code")
                and st.session_state.get("ots_temp_custom_for_table") == table_type_ref
            )
            if temp_active:
                st.caption("Save this as a new custom table")
                save_name = st.text_input(
                    "New table name", key="ots_custom_save_name",
                    label_visibility="collapsed", placeholder="New table name",
                )
                if st.button("\U0001F4BE  Save as custom table", use_container_width=True, key="ots_save_custom_btn"):
                    name = save_name.strip()
                    existing_custom_refs = {r["table_type_ref"] for r in workfile_state.custom_table_rows}
                    if not name:
                        st.error("Enter a name for the new table.")
                    elif name == "temp":
                        st.error("'temp' is reserved and can't be used as a table name.")
                    elif name in TABLE_REGISTRY:
                        # A built-in belongs to the application, not to this
                        # workfile, so its name is refused outright rather
                        # than offered as something to overwrite.
                        st.error(f"'{name}' is a built-in table. Choose a different name.")
                    elif name in existing_custom_refs:
                        _confirm_overwrite_custom_table(workfile_state, name)
                    else:
                        _save_custom_table(workfile_state, name)
                        st.rerun()

        with st.expander("Zoom", expanded=False):
            st.session_state.setdefault("ots_zoom", DEFAULT_ZOOM)
            zoom_choice = st.selectbox(
                "Screen zoom (display only — never saved)", options=ZOOM_OPTIONS,
                key="ots_zoom", label_visibility="collapsed",
            )

        if st.button(
            "\u21ba  Reset", type="primary", key="ots_reset_btn",
            help="Reset — clear the table selection and Preview configuration back to a fresh state",
        ):
            _clear_sandbox_state()
            st.rerun()

    with right:
        if not table_type_ref:
            return

        temp_code = st.session_state.get("ots_temp_custom_code")
        temp_for_table = st.session_state.get("ots_temp_custom_for_table")
        staged_code = temp_code if (temp_code and temp_for_table == table_type_ref) else None
        code_in_force = staged_code or workfile_state.custom_table_code.get(table_type_ref)

        # Everything the finished picture is made of, so a rerun that
        # changes none of it reuses the last one instead of drawing it
        # again -- see ui/common/render_memo.py. chart_store_rows,
        # custom_chart_code and full_unit_set cover the {Cn} chart cells
        # spliced in below, whose own rendering depends on the Chart Store
        # rather than on this table. default_font covers both the table and
        # those cells, since all of them render under it.
        default_font = workfile_state.settings.get("default_font", "")
        signature = render_signature(
            table_type_ref,
            resolved["content"], resolved["column_widths"], resolved["row_heights"],
            width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE,
            tweaks_str, code_in_force,
            workfile_state.chart_store_rows, workfile_state.custom_chart_code, full_unit_set,
            default_font,
        )
        built_in = None if code_in_force else TABLE_REGISTRY.get(table_type_ref)

        def produce_svg():
            with st.spinner("Rendering…"):
                if staged_code:
                    table_func = compile_custom_table(staged_code)
                else:
                    table_func = get_table_callable(table_type_ref, workfile_state.custom_table_code)
                # Called at CHART_RENDER_SCALE times the real target size
                # -- see that constant's own comment -- then displayed
                # below at the real, unmultiplied px width, so the browser
                # shrinks it back down exactly as PowerPoint does.
                # chart_cells (if any) comes back in that same inflated
                # space, so the splice below must use the same inflated
                # width_emu/height_emu, not the real display ones.
                with render_font(default_font):
                    image_bytes, chart_cells = table_func(
                        resolved["content"], resolved["column_widths"], resolved["row_heights"],
                        width_emu=width_emu * CHART_RENDER_SCALE, height_emu=height_emu * CHART_RENDER_SCALE,
                        tweaks=tweaks_str,
                    )
                svg = image_bytes.read().decode("utf-8")
                if chart_cells:
                    svg = _splice_chart_cells_into_svg(
                        svg, chart_cells, workfile_state, full_unit_set,
                        width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE,
                    )
                return svg

        try:
            svg_text = remember_render("ots_render_memo", signature, produce_svg, identity=built_in)
        except Exception as e:
            st.error(f"Table failed to render: {e}")
            return

        if zoom_choice == "Fit to screen":
            st.markdown(_svg_preview_html(svg_text, "100%", default_font), unsafe_allow_html=True)
        else:
            multiplier = ZOOM_MULTIPLIERS.get(zoom_choice, 1.0)
            px_width = max(50, int((width_emu / 914400) * 96 * multiplier))
            st.markdown(
                _svg_preview_html(svg_text, f"{px_width}px", default_font),
                unsafe_allow_html=True,
            )
