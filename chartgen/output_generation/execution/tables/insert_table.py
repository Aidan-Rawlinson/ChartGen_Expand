"""
insert_table.py
Running Order function: insert_table. Renders an Output Table, a grid of
constant text and resolved Stat Tag values composited to a single image by a
Base Table function, and inserts it at the row's position. The Output Table
equivalent of insert_chart, in its own module.

An Output Table is defined independently of any Running Order row. table_id
anchors an insert_table row to one of WorkfileState.output_tables, not the
other way round.

table_type_ref resolves built-in first, then against this workfile's saved
Custom Tables. A custom table behaves identically to a built-in from here on.

A Base Table returns (image_bytes, chart_cells), chart_cells being
{tag: {"x", "y", "width", "height"}} in EMU, one entry per "{Cn}" cell it
reserved space for. For each, the Chart Store entry it names is rendered at
that rectangle, never the entry's own stored size, and inserted as a second
picture layered over the table's own. A chart inside a table is always a
layered PowerPoint shape, never merged image data.

A Chart Store entry's blank populations field inherits the Running Order
default, the same rule an insert_chart row follows.
"""

from dataclasses import replace as _dc_replace

from chartgen.output_generation.execution.results import ok_result, err_result
from chartgen.output_generation.execution.tables.resolve import resolve_output_table
from chartgen.output_generation.execution.tables.custom_tables.resolve import get_table_callable
from chartgen.output_generation.execution.svg_insert import add_svg_picture
from chartgen.output_generation.execution.charts.cache_reader import load_shape
from chartgen.output_generation.execution.charts.custom_charts import get_chart_callable
from chartgen.shared.normalisation_containers.cut_resolution import prepare_chart_cut
from chartgen.shared.normalisation_containers.population_layers import build_population_layers

# A Base Table's returned chart_cells rectangle comes back in inflated
# space, since the table derives it from the width_emu/height_emu it was
# given. Divide by CHART_RENDER_SCALE before using it as a real slide
# placement offset. Do NOT divide before the embedded chart's own render
# call: the raw rectangle is already what a Base Chart expects.
#
# The value must still match TEXT_SCALE in every base_tables/ and
# base_charts/ file, which cannot import it. Full mechanism in
# tables/base_tables/CLAUDE.md.
from chartgen.shared.infrastructure.render_scale import CHART_RENDER_SCALE


def _render_chart_store_chart(ctx, chart_store_row: dict, chart_rect: dict, workfile_state):
    """
    Render one Chart Store entry's own saved chart-def, sized to
    chart_rect, the Base Table's own reserved rectangle for this cell. A
    chart in a table cell is always drawn to fit the cell, never its own
    stored size.

    Runs the same cache-load, cut, population-layers and render pipeline
    insert_chart uses, sourced from a Chart Store row. Returns None on any
    failure: one broken chart cell does not abort the whole table.

    chart_rect is in the *render*-space the enclosing Base Table was
    actually called at (already CHART_RENDER_SCALE times the real cell
    size -- see that constant's own comment), not the real placement
    size -- so chart_rect["width"]/["height"] are used here exactly as
    given, with no further multiplication, matching what a Base Chart
    expects to receive under this same mechanism. The caller
    (insert_table) is responsible for dividing this same rectangle back
    down by CHART_RENDER_SCALE when it comes to placing the *result* on
    the slide.
    """
    cache_file = str(chart_store_row.get("cache_file", "") or "").strip()
    base_chart_name = str(chart_store_row.get("base_chart_name", "") or "").strip()
    if not cache_file or not base_chart_name:
        return None

    # A blank populations field inherits the Running Order default, the same
    # rule any insert_chart row follows. ctx.default_populations is set by a
    # set_default_populations row earlier in this run.
    row_populations = str(chart_store_row.get("populations", "") or "").strip()
    populations_str = row_populations if row_populations else ctx.default_populations

    try:
        data_shape, shape_type = load_shape(cache_file, workfile_state)
    except Exception:
        return None

    start_period = str(chart_store_row.get("start_period", "") or "").strip()
    end_period = str(chart_store_row.get("end_period", "") or "").strip()
    metric_periods_str = str(chart_store_row.get("metric_periods", "") or "").strip()

    try:
        data_shape, _, target_rows, selected_ids = prepare_chart_cut(
            data_shape, shape_type, start_period, end_period, metric_periods_str,
            workfile_state.tables, workfile_state.table_order, ctx.full_unit_set or {},
        )
    except Exception:
        # An unresolvable metric_periods id does not raise; it arrives as a
        # metric with no data. So this catches genuinely unexpected failures
        # only, and still returns None rather than aborting the table.
        return None

    population_layers = []
    if ctx.report_context is not None and populations_str:
        try:
            population_layers = build_population_layers(
                data_shape, populations_str, target_rows, selected_ids
            )
        except Exception:
            population_layers = []
    if not population_layers:
        population_layers = [_dc_replace(data_shape, population_label="All")]

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


def insert_table(ctx, row: dict, settings: dict) -> dict:
    """Render an Output Table and insert it at the row's stored position."""
    if ctx.prs is None:
        return err_result(row, "insert_table: no open presentation (create_ppt not called?).")

    table_id = str(row.get("table_id", "") or "").strip()
    table_type_ref = str(row.get("table_type_ref", "") or "").strip()
    slide_index = _int_or_none(row.get("slide_index"))

    left_emu = _int_or_none(row.get("left_emu"))
    top_emu = _int_or_none(row.get("top_emu"))
    width_emu = _int_or_none(row.get("width_emu"))
    height_emu = _int_or_none(row.get("height_emu"))

    missing = []
    if not table_id: missing.append("table_id")
    if not table_type_ref: missing.append("table_type_ref")
    if slide_index is None: missing.append("slide_index")
    if None in (left_emu, top_emu, width_emu, height_emu):
        missing.append("position/size EMU values")
    if missing:
        return err_result(row, f"insert_table: missing required fields: {', '.join(missing)}")

    workfile_state = settings.get("workfile_state")
    grid_rows = workfile_state.output_tables.get(table_id) if workfile_state else None
    if not grid_rows:
        return err_result(row, f"insert_table: no Output Table found for table_id '{table_id}'.")

    resolved = resolve_output_table(grid_rows, workfile_state, ctx.full_unit_set or {})

    tweaks = str(row.get("tweaks", "") or "").strip()
    custom_table_code = workfile_state.custom_table_code if workfile_state else {}
    try:
        table_func = get_table_callable(table_type_ref, custom_table_code)
        # Called at CHART_RENDER_SCALE times the row's real target size
        # (see that constant's own comment) -- image_bytes comes back
        # drawn at that inflated size; chart_cells comes back in that
        # same inflated space too, since a Base Table derives it
        # proportionally from whatever width_emu/height_emu it's given.
        image_bytes, chart_cells = table_func(
            resolved["content"], resolved["column_widths"], resolved["row_heights"],
            width_emu=width_emu * CHART_RENDER_SCALE, height_emu=height_emu * CHART_RENDER_SCALE,
            tweaks=tweaks,
        )
    except Exception as e:
        return err_result(row, f"insert_table: render failed for '{table_type_ref}': {e}")

    try:
        slide = ctx.prs.slides[slide_index]
        # Every Base Table returns SVG bytes -- inserted via the shared add_svg_picture
        # dual-blip mechanism rather than a plain add_picture call. Placed
        # at the row's real, unmultiplied width_emu/height_emu -- the
        # inflated image_bytes shrinks back down to this on the slide,
        # exactly as for a chart (assembly_engine.insert_chart).
        add_svg_picture(
            slide, image_bytes.read(), left_emu, top_emu, width_emu, height_emu,
        )
    except Exception as e:
        return err_result(row, f"insert_table: failed to insert image on slide {slide_index}: {e}")

    chart_cells_by_id = {
        r.get("chart_store_id"): r for r in (workfile_state.chart_store_rows if workfile_state else [])
    }
    placed = 0
    skipped = 0
    for chart_tag, rect in (chart_cells or {}).items():
        chart_store_row = chart_cells_by_id.get(chart_tag)
        if chart_store_row is None:
            skipped += 1
            continue
        # rect is in the table's own render-space (CHART_RENDER_SCALE
        # times real size -- see that constant's own comment). Passed to
        # the chart's own render call exactly as given (chart_rect there
        # already is the correct inflated size a Base Chart expects), but
        # divided back down by CHART_RENDER_SCALE here, for placement
        # only, to convert it into a real slide-EMU offset/size relative
        # to the table's own real (left_emu, top_emu) position.
        chart_image_bytes = _render_chart_store_chart(ctx, chart_store_row, rect, workfile_state)
        if chart_image_bytes is None:
            skipped += 1
            continue
        try:
            add_svg_picture(
                slide, chart_image_bytes.read(),
                left_emu + int(round(rect["x"] / CHART_RENDER_SCALE)),
                top_emu + int(round(rect["y"] / CHART_RENDER_SCALE)),
                int(round(rect["width"] / CHART_RENDER_SCALE)),
                int(round(rect["height"] / CHART_RENDER_SCALE)),
            )
            placed += 1
        except Exception:
            skipped += 1

    chart_note = f" ({placed} chart cell(s) placed" + (f", {skipped} skipped)" if skipped else ")") if (placed or skipped) else ""
    return ok_result(row, f"Output Table '{table_id}' inserted (slide {slide_index + 1}){chart_note}")


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
