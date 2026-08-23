"""
output_tables_tab.py
Output Tables: grid-based tables rendered as a single image, the table
equivalent of a Base Chart. Authored here rather than on the Charts sheet,
since an Output Table's content model does not fit CHART_SANDBOX_FIELDS.

One selection, at the top: a "Select Table" box holding both entry points,
a Running Order row (bound mode) and an Output Table by name (free-play).
"+ New Output Table" sits last in that list and reveals an inline
Name/Create control. Everything below acts on that one selection. There is
no second selector anywhere on the tab.

Edit Grid is content authoring: the raw c0..cN grid, resize, Update, and the
Excel round-trip. Preview mirrors the Charts sheet's mechanics wherever the
concepts match: table type, tweaks, sizing in percent, save-back via
row_ops.py, Custom Tables, and Reset. Reset clears Preview's own
configuration only, never the table selection, which lives in the shared box
above.

A "{Cn}" chart-component cell references a Chart Store entry, rendered live
in Preview as a nested <image> spliced into the table's own SVG, and in the
final report as a layered PowerPoint picture. Neither path composites the
two SVG documents into one.

Creating a table here also appends an insert_table row immediately above
save_ppt, with no slide or position yet.
"""

import base64
import json
import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from chartgen.output_generation.definition.running_order import (
    TABLE_SANDBOX_FIELDS, overwrite_row_fields, insert_new_row,
    append_content_row_above_footer,
)
from chartgen.output_generation.execution.charts.chart_store import resolve_chart_store_population_layers
from chartgen.output_generation.execution.charts.custom_charts import get_chart_callable
from chartgen.output_generation.execution.tables.base_tables import TABLE_REGISTRY
from chartgen.output_generation.execution.tables.custom_tables.bundle import build_bundle
from chartgen.output_generation.execution.tables.custom_tables.gate import (
    validate_custom_table_code, compile_custom_table, CustomTableError,
)
from chartgen.output_generation.execution.tables.custom_tables.resolve import (
    get_table_callable, custom_table_descriptions, all_table_type_refs,
)
from chartgen.output_generation.execution.tables.grid_store import (
    next_table_id, new_grid, resize_grid, validate_grid,
    DEFAULT_TABLE_ROWS, DEFAULT_TABLE_COLUMNS,
)
from chartgen.output_generation.execution.tables.grid_xlsx import (
    write_output_table_xlsx, read_output_table_xlsx,
)
from chartgen.output_generation.execution.tables.resolve import resolve_output_table
from chartgen.shared.infrastructure.cg_extracts import get_extracts_folder
from chartgen.shared.infrastructure.page_sizing import (
    percent_to_emu, emu_to_percent, get_page_size_emu,
    has_known_template_page_size, STANDARD_PAGE_SIZES_EMU, DEFAULT_STANDARD_PAGE_SIZE,
)
from chartgen.shared.infrastructure.report_context import build_report_context
from chartgen.shared.infrastructure.soft_parents import resolve_full_unit_set
from chartgen.ui.common.guidance import render_tab_header
from chartgen.ui.common.pickers import pick_xlsx_file
from chartgen.workfile.state.session_state import ws, settings, master_table

NEW_TABLE_OPTION = "+ New Output Table"
RO_PLACEHOLDER = "- Running order line -"
TABLE_PLACEHOLDER = "- Saved Table -"
TARGET_PLACEHOLDER = "- Select target row -"

# Screen zoom for the Preview image. Display only, never saved.
#
# An explicit pixel width is required: st.image() otherwise shows the render
# at its full native resolution rather than a size reflecting the configured
# width and height percentage.
ZOOM_OPTIONS = ["0.75x", "Actual size (approximately)", "1.25x", "1.5x", "2x", "Fit to screen"]
ZOOM_MULTIPLIERS = {"0.75x": 0.75, "Actual size (approximately)": 1.0, "1.25x": 1.25, "1.5x": 1.5, "2x": 2.0}
DEFAULT_ZOOM = "Actual size (approximately)"

# MUST match TEXT_SCALE in every file that defines one, and the
# copies in assembly_engine.py, insert_table.py and charts_tab.py. Nothing
# enforces this and a mismatch fails silently. Full mechanism in
# output_generation/execution/tables/base_tables/CLAUDE.md.
#
# Applied to the table_func render call below and to
# _splice_chart_cells_into_svg, which must receive the same inflated value
# table_func was called with, since chart_cells comes back in that space.
# The CSS display width stays at the real, unmultiplied size.
CHART_RENDER_SCALE = 5

# "ots_" is Preview's own configuration state (table type, tweaks, sizing,
# save-back target, paste-back) -- what Reset clears. Table *selection*
# ("ot_ro_choice", "ot_table_choice", "ot_bound_row_idx", ...) lives outside
# that prefix on purpose, so Reset never disturbs which table is selected.
OTS_KEY_PREFIX = "ots_"


def _svg_preview_html(svg_text, width_css):
    """
    Forces an SVG's rendered size to width_css (a CSS width value, e.g.
    "480px" or "100%") via an inline style on the SVG's own root element,
    since st.markdown has no width parameter the way st.image does. Used
    instead of st.image because st.image goes through PIL, which can't
    decode SVG, and every Base Table returns SVG bytes.
    """
    styled = svg_text.replace("<svg ", '<svg style="width:100%;height:auto;display:block" ', 1)
    return f'<div style="width:{width_css}">{styled}</div>'


def _render_chart_store_chart_preview(chart_store_row: dict, chart_rect: dict,
                                       workfile_state, full_unit_set: dict):
    """
    Preview-side equivalent of insert_table.py's own
    _render_chart_store_chart -- population_layers resolution itself is
    shared (chart_store.resolve_chart_store_population_layers), so this
    function only adds what's specific to actually rendering: the
    base_chart_name lookup and the render call at the cell's own rectangle.
    Returns None on any failure -- one broken chart cell doesn't block the
    rest of the preview.

    chart_rect is in the table's own render-space (CHART_RENDER_SCALE
    times real size -- see that constant's own comment), since the
    enclosing table_func call is. Used here exactly as given, with no
    further multiplication -- that's already the correctly-inflated size
    a Base Chart expects to be called with under this same mechanism.
    """
    base_chart_name = str(chart_store_row.get("base_chart_name", "") or "").strip()
    if not base_chart_name:
        return None

    population_layers = resolve_chart_store_population_layers(chart_store_row, workfile_state, full_unit_set)
    if not population_layers:
        return None

    tweaks = str(chart_store_row.get("tweaks", "") or "").strip()
    try:
        chart_func = get_chart_callable(base_chart_name, workfile_state.custom_chart_code)
        return chart_func(
            population_layers,
            width_emu=int(round(chart_rect["width"])),
            height_emu=int(round(chart_rect["height"])),
            tweaks=tweaks,
        )
    except Exception:
        return None


def _splice_chart_cells_into_svg(table_svg_text: str, chart_cells: dict, workfile_state,
                                  full_unit_set: dict, width_emu: int, height_emu: int) -> str:
    """
    Preview-only compositing: embeds each chart cell's own rendered chart
    as a nested <image> data URI inside the table's own SVG, positioned as
    a percentage of the table's own declared width/height (recovered from
    each cell's EMU rectangle) rather than absolute pixels -- percentages
    resolve against whatever the table's own SVG viewport actually ends up
    being (post any bbox_inches="tight" crop, post the CSS stretch
    _svg_preview_html applies), so this stays visually aligned with the
    cell borders the same Base Table function drew, which used the exact
    same percent coordinates internally, rather than needing to reverse-
    engineer matplotlib's own crop margins from outside it.

    Only for on-screen preview -- the final report instead layers a
    separate PowerPoint picture (insert_table.py), never merges SVG
    documents: an <image> reference is fully opaque to the
    browser, so there's no risk of the two SVGs' own internal ids/styles
    colliding the way directly inlining one SVG's markup into another's
    would be.
    """
    if not chart_cells or not width_emu or not height_emu:
        return table_svg_text

    chart_store_by_id = {r.get("chart_store_id"): r for r in workfile_state.chart_store_rows}
    inserts = []
    for tag, rect in chart_cells.items():
        chart_store_row = chart_store_by_id.get(tag)
        if chart_store_row is None:
            continue
        chart_image_bytes = _render_chart_store_chart_preview(
            chart_store_row, rect, workfile_state, full_unit_set
        )
        if chart_image_bytes is None:
            continue
        b64 = base64.b64encode(chart_image_bytes.read()).decode("ascii")
        x_pct = (rect["x"] / width_emu) * 100
        y_pct = (rect["y"] / height_emu) * 100
        w_pct = (rect["width"] / width_emu) * 100
        h_pct = (rect["height"] / height_emu) * 100
        inserts.append(
            f'<image x="{x_pct}%" y="{y_pct}%" width="{w_pct}%" height="{h_pct}%" '
            f'xlink:href="data:image/svg+xml;base64,{b64}" preserveAspectRatio="none" />'
        )

    if not inserts:
        return table_svg_text
    idx = table_svg_text.rfind("</svg>")
    if idx == -1:
        return table_svg_text
    return table_svg_text[:idx] + "".join(inserts) + table_svg_text[idx:]


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clear_sandbox_state():
    """
    Full reset -- clears both the shared table selection ("ot_" prefix)
    and Preview's own configuration ("ots_" prefix), mirroring the Charts
    sheet's Reset exactly (a single prefix there; two here, both wiped
    together) so a person can move on to a different table in one click.
    "ot_tab_rendered" is preserved so this doesn't re-trigger the once-per-
    Open restore from settings["output_tables_sheet_state"], which would
    otherwise silently undo the reset.
    """
    keep = {"ot_tab_rendered"}
    for k in list(st.session_state.keys()):
        if (k.startswith("ot_") or k.startswith(OTS_KEY_PREFIX)) and k not in keep:
            del st.session_state[k]


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


# ---------------------------------------------------------------------------
# Sandbox state persistence (settings["output_tables_sheet_state"]),
# mirroring charts_tab.py's capture_charts_sheet_state / _restore_charts_sheet_state
# field-for-field for the table domain.
# ---------------------------------------------------------------------------

def _restore_output_tables_sheet_state(workfile_state, the_settings, row_id_to_idx):
    raw = (the_settings or {}).get("output_tables_sheet_state", "")
    if not raw:
        return
    try:
        state = json.loads(raw)
    except (TypeError, ValueError):
        return

    table_id = state.get("table_id", "")
    if table_id in workfile_state.output_tables:
        name = next(
            (r["table_name"] for r in workfile_state.output_table_rows if r["table_id"] == table_id), ""
        )
        if name:
            st.session_state["ot_table_choice"] = name
            st.session_state["ot_last_table_choice"] = name
            st.session_state["ot_selected_table_id"] = table_id

    ro_row_id = state.get("ro_row_id")
    if ro_row_id in row_id_to_idx:
        st.session_state["ot_ro_choice"] = ro_row_id
        st.session_state["ot_last_loaded_ro"] = ro_row_id
        st.session_state["ot_bound_row_idx"] = row_id_to_idx[ro_row_id]
    else:
        st.session_state["ot_ro_choice"] = RO_PLACEHOLDER
        st.session_state["ot_last_loaded_ro"] = RO_PLACEHOLDER

    st.session_state["ots_table_type_ref"] = state.get("table_type_ref", "plain_grid")
    st.session_state["ots_tweaks_str"] = state.get("tweaks", "")

    # A persisted value is shown exactly as stored, however small or large.
    # The Sizing box is a save-back surface, so any number substituted here
    # gets committed to the row on the next save. A value that will not
    # parse at all is reported rather than replaced silently; the key is
    # left unset and the setdefault further down supplies the starting
    # value, with the user told why.
    for key, label in (("width_pct", "Width"), ("height_pct", "Height")):
        raw = state.get(key, 50.0)
        try:
            st.session_state["ots_" + key] = float(raw)
        except (TypeError, ValueError):
            st.error(
                f"Stored Preview {label.lower()} ({raw!r}) is not a number, so it could not be "
                f"restored. The box below shows a starting value, not your stored one. Use Reset "
                f"to clear the saved Preview configuration."
            )

    manual_page_size = state.get("manual_page_size")
    if manual_page_size in STANDARD_PAGE_SIZES_EMU:
        st.session_state["ots_manual_page_size"] = manual_page_size

    action = state.get("action", "Overwrite selected row")
    if action in ("Overwrite selected row", "Insert above selected row", "Insert below selected row"):
        st.session_state["ots_action"] = action

    target_row_id = state.get("target_row_id")
    if target_row_id in row_id_to_idx:
        st.session_state["ots_target_row_choice"] = target_row_id


def capture_output_tables_sheet_state(workfile_state):
    """
    Snapshot the tab's current table selection and Preview configuration
    into settings["output_tables_sheet_state"] (JSON), called just before
    Save/Save As/Save and Close (sidebar.py, save_as_form.py), mirroring
    capture_charts_sheet_state.
    """
    if "ot_tab_rendered" not in st.session_state:
        return

    ro_choice = st.session_state.get("ot_ro_choice", RO_PLACEHOLDER)
    target_choice = st.session_state.get("ots_target_row_choice", TARGET_PLACEHOLDER)

    state = {
        "table_id": st.session_state.get("ot_selected_table_id", ""),
        "ro_row_id": ro_choice if ro_choice != RO_PLACEHOLDER else None,
        "table_type_ref": st.session_state.get("ots_table_type_ref", "plain_grid"),
        "tweaks": st.session_state.get("ots_tweaks_str", ""),
        "width_pct": st.session_state.get("ots_width_pct", 50.0),
        "height_pct": st.session_state.get("ots_height_pct", 50.0),
        "manual_page_size": st.session_state.get("ots_manual_page_size"),
        "action": st.session_state.get("ots_action", "Overwrite selected row"),
        "target_row_id": target_choice if target_choice != TARGET_PLACEHOLDER else None,
    }
    workfile_state.settings["output_tables_sheet_state"] = json.dumps(state)


# ---------------------------------------------------------------------------
# Tab entry point -- the one shared "Select Table" box, then mode + content
# ---------------------------------------------------------------------------

def render_output_tables_tab():
    render_tab_header("Output Tables and Grids", "output_tables")

    workfile_state = ws()
    the_settings = settings()

    table_rows = workfile_state.output_table_rows
    name_to_id = {r["table_name"]: r["table_id"] for r in table_rows}
    id_to_name = {v: k for k, v in name_to_id.items()}
    table_names = list(name_to_id.keys())

    ro_rows = workfile_state.running_order_rows
    row_id_to_idx = {
        r["row_id"]: i for i, r in enumerate(ro_rows) if str(r.get("function", "")) == "insert_table"
    }
    table_row_ids = list(row_id_to_idx.keys())

    def ro_row_label(row_id):
        r = ro_rows[row_id_to_idx[row_id]]
        tid = str(r.get("table_id", "") or "")
        tname = id_to_name.get(tid, tid or "— no table —")
        ttype = str(r.get("table_type_ref", "") or "— no type —")
        return f"Row {row_id}: {ttype} · {tname}"

    def format_row_choice(v):
        return v if v == RO_PLACEHOLDER else ro_row_label(v)

    if "ot_tab_rendered" not in st.session_state:
        st.session_state["ot_tab_rendered"] = True
        _restore_output_tables_sheet_state(workfile_state, the_settings, row_id_to_idx)

    # Applied here, before the "Running Order row" selectbox below is
    # created, per the widget-bound-key restriction explained where this is
    # staged (Save to Running Order's success branch).
    if "ot_pending_ro_choice_after_save" in st.session_state:
        pending_ro = st.session_state.pop("ot_pending_ro_choice_after_save")
        if pending_ro in table_row_ids:
            st.session_state["ot_ro_choice"] = pending_ro
            # Also sync "last loaded" and the bound row index so the RO-row
            # detection block below sees this as unchanged, not a fresh
            # selection, and doesn't recompute Sizing from EMU a second
            # time — that redundant reload-after-save was the source of
            # the Sizing box occasionally going stale right after a save,
            # not a genuine new load.
            st.session_state["ot_last_loaded_ro"] = pending_ro
            st.session_state["ot_bound_row_idx"] = row_id_to_idx[pending_ro]

    if st.session_state.get("ot_ro_choice") not in ([RO_PLACEHOLDER] + table_row_ids):
        st.session_state["ot_ro_choice"] = RO_PLACEHOLDER

    with st.expander("Select Table", expanded=True):
        ro_choice = st.selectbox(
            "Running Order row", options=[RO_PLACEHOLDER] + table_row_ids,
            format_func=format_row_choice, key="ot_ro_choice",
        )

        last_loaded_ro = st.session_state.get("ot_last_loaded_ro", "__unset__")
        if ro_choice != last_loaded_ro:
            st.session_state["ot_last_loaded_ro"] = ro_choice
            if ro_choice == RO_PLACEHOLDER:
                st.session_state.pop("ot_bound_row_idx", None)
            else:
                row_idx = row_id_to_idx[ro_choice]
                row = ro_rows[row_idx]
                row_table_id = str(row.get("table_id", "") or "")
                page_w, page_h = get_page_size_emu(the_settings, st.session_state.get("ots_manual_page_size"))
                w_emu = _int_or_none(row.get("width_emu"))
                h_emu = _int_or_none(row.get("height_emu"))

                st.session_state["ot_bound_row_idx"] = row_idx
                st.session_state["ot_pending_table_choice"] = id_to_name.get(row_table_id)
                st.session_state["ots_pending_table_type_ref"] = str(row.get("table_type_ref", "") or "")
                st.session_state["ots_pending_tweaks_str"] = str(row.get("tweaks", "") or "")
                # The computed percentage is shown as it is, however small.
                # A tiny value means the row's stored EMU really is tiny
                # relative to the page, and that is what the widget should
                # say.
                width_pct_computed = round(emu_to_percent(w_emu, page_w, page_h), 2) if w_emu else 0.0
                height_pct_computed = round(emu_to_percent(h_emu, page_w, page_h), 2) if h_emu else 0.0
                st.session_state["ots_width_pct"] = width_pct_computed
                st.session_state["ots_height_pct"] = height_pct_computed
                st.session_state["ots_target_row_choice"] = ro_choice

        if "ot_pending_table_choice" in st.session_state:
            pending_label = st.session_state.pop("ot_pending_table_choice")
            if pending_label is not None:
                st.session_state["ot_table_choice"] = pending_label
        st.session_state.setdefault("ot_table_choice", TABLE_PLACEHOLDER)
        if st.session_state["ot_table_choice"] not in ([TABLE_PLACEHOLDER] + table_names + [NEW_TABLE_OPTION]):
            st.session_state["ot_table_choice"] = TABLE_PLACEHOLDER

        table_choice = st.selectbox(
            "Output Table", options=[TABLE_PLACEHOLDER] + table_names + [NEW_TABLE_OPTION], key="ot_table_choice",
        )

        if table_choice == NEW_TABLE_OPTION:
            _render_new_table_form(workfile_state, name_to_id, the_settings)

    if table_choice in (TABLE_PLACEHOLDER, NEW_TABLE_OPTION):
        return

    table_id = name_to_id[table_choice]
    st.session_state["ot_selected_table_id"] = table_id
    grid_rows = workfile_state.output_tables.get(table_id)
    if grid_rows is None:
        st.error("This Output Table's grid could not be found -- it may have been removed from the workfile.")
        return

    bound_row_idx = st.session_state.get("ot_bound_row_idx")
    if bound_row_idx is not None:
        bound_table_id = str(ro_rows[bound_row_idx].get("table_id", "") or "")
        if bound_table_id and bound_table_id != table_id:
            st.warning(
                "The bound Running Order row references a different Output "
                f"Table ('{id_to_name.get(bound_table_id, bound_table_id)}')."
            )

    st.session_state.setdefault("ot_mode", "Edit Grid")
    mode = st.radio(
        "Mode", options=["Edit Grid", "Preview"], key="ot_mode",
        horizontal=True, label_visibility="collapsed",
    )

    # Re-assert width_pct/height_pct from the bound row's stored EMU at the
    # moment Preview is entered, not only when the row was selected.
    #
    # Edit Grid is the default mode, so the original assignment happens while
    # the Sizing widget does not yet exist. Without this re-assertion
    # immediately before that widget's first mount, the box displays its own
    # min_value rather than the correct value, even though session_state
    # holds the right number throughout. Verified by testing.
    previous_mode = st.session_state.get("ot_previous_mode")
    entering_preview = (mode == "Preview" and previous_mode != "Preview")
    st.session_state["ot_previous_mode"] = mode

    if mode == "Preview" and entering_preview and bound_row_idx is not None:
        bound_row = ro_rows[bound_row_idx]
        page_w_r, page_h_r = get_page_size_emu(the_settings, st.session_state.get("ots_manual_page_size"))
        w_emu_r = _int_or_none(bound_row.get("width_emu"))
        h_emu_r = _int_or_none(bound_row.get("height_emu"))
        if w_emu_r:
            st.session_state["ots_width_pct"] = round(emu_to_percent(w_emu_r, page_w_r, page_h_r), 2)
        if h_emu_r:
            st.session_state["ots_height_pct"] = round(emu_to_percent(h_emu_r, page_w_r, page_h_r), 2)

    if mode == "Edit Grid":
        _render_grid_editor(workfile_state, table_id, grid_rows)
    else:
        _render_preview_sandbox(
            workfile_state, the_settings, table_id, grid_rows,
            table_row_ids, row_id_to_idx, id_to_name, ro_rows, ro_choice, format_row_choice,
        )


def _render_new_table_form(workfile_state, name_to_id, the_settings):
    st.caption("Create a new Output Table")
    new_name = st.text_input("Name", key="ot_new_name")

    if st.button("Create Output Table", type="primary", key="ot_create_table_btn"):
        name = new_name.strip()
        if not name:
            st.error("Enter a name.")
        elif name in name_to_id:
            st.error(f"'{name}' already exists. Choose a different name.")
        else:
            # Both the index rows and the grid store, since either can hold
            # an id the settings counter never saw.
            ids_in_use = {r.get("table_id") for r in workfile_state.output_table_rows}
            ids_in_use |= set(workfile_state.output_tables)
            table_id = next_table_id(workfile_state.settings, ids_in_use)
            workfile_state.output_tables[table_id] = new_grid(table_id, DEFAULT_TABLE_ROWS, DEFAULT_TABLE_COLUMNS)
            workfile_state.output_table_rows.append({
                "table_id": table_id, "table_name": name,
                "rows": str(DEFAULT_TABLE_ROWS), "columns": str(DEFAULT_TABLE_COLUMNS),
            })

            # Automatic Running Order placement -- no real
            # slide/position yet (that's for the user to sort out via this
            # tab's own Preview sandbox or the Running Order tab), but the
            # row exists from the moment the table does, rather than
            # requiring a manual Insert above/below via Preview first.
            page_w, page_h = get_page_size_emu(the_settings, None)
            append_content_row_above_footer(workfile_state.running_order_rows, {
                "function":       "insert_table",
                "table_id":       table_id,
                "table_type_ref": "plain_grid",
                "width_emu":      percent_to_emu(70.0, page_w, page_h),
                "height_emu":     percent_to_emu(50.0, page_w, page_h),
                "notes":          "Output Table",
            })

            workfile_state.dirty = True
            # "ot_table_choice" is a widget-bound key that's already been
            # instantiated earlier in this same run (the "Output Table"
            # selectbox above, in the shared "Select Table" box) -- can't be
            # written to directly here, same restriction as the Save to
            # Running Order success branch further down. Staged in the
            # existing "pending" key instead; applied at the top of
            # render_output_tables_tab, before that selectbox is created on
            # the next run.
            st.session_state["ot_pending_table_choice"] = name
            st.success(f"Created '{name}'.")
            st.rerun()


# ---------------------------------------------------------------------------
# Edit Grid mode -- content authoring for the selected Output Table
# ---------------------------------------------------------------------------

def _render_grid_editor(workfile_state, table_id, grid_rows):
    with st.expander("Resize grid", expanded=False):
        n_rows = max(0, len(grid_rows) - 1)
        n_cols = max(0, len(grid_rows[0]) - 1) if grid_rows else 0
        col_a, col_b = st.columns(2)
        with col_a:
            new_n_rows = st.number_input(
                "Rows", min_value=1, max_value=200, value=n_rows, step=1, key="ot_resize_rows",
            )
        with col_b:
            new_n_cols = st.number_input(
                "Columns", min_value=1, max_value=200, value=n_cols, step=1, key="ot_resize_cols",
            )
        if st.button("Apply resize", key="ot_apply_resize_btn"):
            resized = resize_grid(grid_rows, int(new_n_rows), int(new_n_cols), table_id)
            workfile_state.output_tables[table_id] = resized
            for idx_row in workfile_state.output_table_rows:
                if idx_row["table_id"] == table_id:
                    idx_row["rows"] = str(int(new_n_rows))
                    idx_row["columns"] = str(int(new_n_cols))
                    break
            workfile_state.dirty = True
            st.success("Grid resized.")
            st.rerun()

    df = pd.DataFrame(grid_rows)
    edited_df = st.data_editor(df, use_container_width=True, key=f"ot_grid_editor_{table_id}")

    col_update, col_dl, col_ul = st.columns([1, 1, 1])

    update_clicked = col_update.button(
        "Update", type="primary", use_container_width=True, key=f"ot_grid_update_{table_id}",
    )
    if update_clicked:
        new_grid_rows = edited_df.astype(str).to_dict(orient="records")
        warnings = validate_grid(new_grid_rows)
        workfile_state.output_tables[table_id] = new_grid_rows
        workfile_state.dirty = True
        if warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.success("Grid updated.")

    extracts_dir = get_extracts_folder(workfile_state.workfile_path)

    if col_dl.button(
        "\u2b07  Export to CG_Extracts", use_container_width=True, key=f"ot_grid_export_{table_id}",
    ):
        export_path = os.path.join(extracts_dir, f"{table_id}_grid.xlsx")
        write_output_table_xlsx(grid_rows, workfile_state.text_stats_rows, export_path)
        st.success(f"Exported to {export_path}")

    if col_ul.button(
        "\u2b06  Import from CG_Extracts", use_container_width=True, key=f"ot_grid_import_{table_id}",
    ):
        picked_path = pick_xlsx_file(extracts_dir, "Select edited grid Excel file")
        if picked_path:
            try:
                imported_grid = read_output_table_xlsx(picked_path)
            except Exception as e:
                st.error(f"Excel import failed: {e}")
                st.stop()
            workfile_state.output_tables[table_id] = imported_grid
            n_rows, n_cols = max(0, len(imported_grid) - 1), (max(0, len(imported_grid[0]) - 1) if imported_grid else 0)
            for idx_row in workfile_state.output_table_rows:
                if idx_row["table_id"] == table_id:
                    idx_row["rows"] = str(n_rows)
                    idx_row["columns"] = str(n_cols)
                    break
            workfile_state.dirty = True
            warnings = validate_grid(imported_grid)
            st.session_state["ot_grid_import_warnings"] = warnings
            st.rerun()

    import_warnings = st.session_state.pop("ot_grid_import_warnings", None)
    if import_warnings:
        for w in import_warnings:
            st.warning(w)


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
        resolved = resolve_output_table(grid_rows, workfile_state, full_unit_set)

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
                st.success("Saved to Running Order.")
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
            full_unit_set_for_bundle = _current_full_unit_set(workfile_state, the_settings) if include_charts else None

            # width_emu/height_emu passed here at CHART_RENDER_SCALE times
            # the real target size -- the same inflated value this table
            # is actually called with at runtime (see that constant's own
            # comment), so the bundle's own "Live data for this table,
            # right now" section reports the true figures an AI author
            # needs to reason about.
            bundle_text = build_bundle(
                table_type_ref, resolved["content"], resolved["column_widths"], resolved["row_heights"],
                width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE, tweaks_str, workfile_state.custom_table_code,
                include_charts=include_charts, workfile_state=workfile_state, full_unit_set=full_unit_set_for_bundle,
            )
            st.download_button(
                "\u2b07  Download bundle for this table", data=bundle_text,
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
                    elif name in TABLE_REGISTRY or name in existing_custom_refs:
                        st.error(f"'{name}' is already in use by another table. Choose a different name.")
                    else:
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
                        st.success(f"Saved as '{name}' — now available in Select Visualisation.")
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

        with st.spinner("Rendering…"):
            try:
                if temp_code and temp_for_table == table_type_ref:
                    table_func = compile_custom_table(temp_code)
                else:
                    table_func = get_table_callable(table_type_ref, workfile_state.custom_table_code)
                # Called at CHART_RENDER_SCALE times the real target size
                # -- see that constant's own comment -- then displayed
                # below at the real, unmultiplied px width, so the browser
                # shrinks it back down exactly as PowerPoint does.
                # chart_cells (if any) comes back in that same inflated
                # space, so the splice below must use the same inflated
                # width_emu/height_emu, not the real display ones.
                image_bytes, chart_cells = table_func(
                    resolved["content"], resolved["column_widths"], resolved["row_heights"],
                    width_emu=width_emu * CHART_RENDER_SCALE, height_emu=height_emu * CHART_RENDER_SCALE,
                    tweaks=tweaks_str,
                )
            except Exception as e:
                st.error(f"Table failed to render: {e}")
                return

        svg_text = image_bytes.read().decode("utf-8")
        if chart_cells:
            full_unit_set = _current_full_unit_set(workfile_state, the_settings)
            svg_text = _splice_chart_cells_into_svg(
                svg_text, chart_cells, workfile_state, full_unit_set,
                width_emu * CHART_RENDER_SCALE, height_emu * CHART_RENDER_SCALE,
            )

        if zoom_choice == "Fit to screen":
            st.markdown(_svg_preview_html(svg_text, "100%"), unsafe_allow_html=True)
        else:
            multiplier = ZOOM_MULTIPLIERS.get(zoom_choice, 1.0)
            px_width = max(50, int((width_emu / 914400) * 96 * multiplier))
            st.markdown(
                _svg_preview_html(svg_text, f"{px_width}px"),
                unsafe_allow_html=True,
            )
