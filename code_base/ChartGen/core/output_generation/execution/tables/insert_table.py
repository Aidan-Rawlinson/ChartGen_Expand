"""
insert_table.py
Running Order function: insert_table -- renders an Output Table (a grid of
constant text and resolved Stat Tag values, composited to a single image by
a Base Table function) and inserts it at the row's position. The Output
Table equivalent of insert_chart (assembly_engine.py), kept in its own
module under execution/tables/ rather than folded into assembly_engine,
mirroring how update_text was promoted to its own module under
execution/text/ (Architecture Decision 20).

An Output Table is defined independently of any Running Order row (the
same relationship a Stat Tag has to insert_chart rows) -- table_id anchors
an insert_table row to one of WorkfileState.output_tables, not the other
way round.

table_type_ref is resolved built-in first, then against this workfile's
own saved Custom Tables (get_table_callable) -- a custom table behaves
identically to a built-in from this point on, mirroring insert_chart's own
get_chart_callable resolution exactly.

Chart-component cells (Decision 28) -- a Base Table function returns
(image_bytes, chart_cells), chart_cells being {tag: {"x","y","width",
"height"}} in EMU, one entry per "{Cn}" cell it actually drew space for.
For each one found, the Chart Store entry it names is rendered at that
cell's own EMU rectangle -- never the entry's own stored size -- and
inserted as a second picture, layered on top of the table's own, rather
than composited into the table's own SVG (Decisions.md: charts inside
tables are always layered PowerPoint shapes, not merged image data).
"""

from dataclasses import replace as _dc_replace

from core.output_generation.execution.results import ok_result, err_result
from core.output_generation.execution.tables.resolve import resolve_output_table
from core.output_generation.execution.tables.custom_tables.resolve import get_table_callable
from core.output_generation.execution.svg_insert import add_svg_picture
from core.output_generation.execution.charts.cache_reader import load_shape
from core.output_generation.execution.charts.custom_charts import get_chart_callable
from core.shared.normalisation_containers.cut_resolution import prepare_chart_cut
from core.shared.normalisation_containers.population_layers import build_population_layers


def _render_chart_store_chart(ctx, chart_store_row: dict, chart_rect: dict, workfile_state):
    """
    Render one Chart Store entry's own saved chart-def, sized to
    chart_rect (a Base Table's own reserved rectangle for this cell, in
    EMU) rather than the entry's own stored width_emu/height_emu --
    Decisions.md: a chart embedded in a table cell is always drawn to fit
    the cell, never its own stored size. Mirrors insert_chart's own
    cache-load / cut / population-layers / render pipeline
    (assembly_engine.py) field for field, sourced from a Chart Store row
    instead of a Running Order row. Returns None on any failure -- one
    broken chart cell doesn't abort the whole table.
    """
    cache_file = str(chart_store_row.get("cache_file", "") or "").strip()
    base_chart_name = str(chart_store_row.get("base_chart_name", "") or "").strip()
    if not cache_file or not base_chart_name:
        return None

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
    except ValueError:
        return None

    populations_str = str(chart_store_row.get("populations", "") or "").strip()
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
        image_bytes, chart_cells = table_func(
            resolved["content"], resolved["column_widths"], resolved["row_heights"],
            width_emu=width_emu, height_emu=height_emu, tweaks=tweaks,
        )
    except Exception as e:
        return err_result(row, f"insert_table: render failed for '{table_type_ref}': {e}")

    try:
        slide = ctx.prs.slides[slide_index]
        # Every Base Table returns SVG bytes (see Architecture, SVG
        # rendering methodology) -- inserted via the shared add_svg_picture
        # dual-blip mechanism rather than a plain add_picture call.
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
        chart_image_bytes = _render_chart_store_chart(ctx, chart_store_row, rect, workfile_state)
        if chart_image_bytes is None:
            skipped += 1
            continue
        try:
            add_svg_picture(
                slide, chart_image_bytes.read(),
                left_emu + int(round(rect["x"])), top_emu + int(round(rect["y"])),
                int(round(rect["width"])), int(round(rect["height"])),
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
