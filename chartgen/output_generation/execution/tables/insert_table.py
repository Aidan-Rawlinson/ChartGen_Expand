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

A Chart Store entry's own blank populations field inherits the Running
Order default (ctx.default_populations, set by a set_default_populations
row earlier in the same run) -- the same inherit rule an insert_chart
row's own blank populations field follows.
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

# PowerPoint SVG-text-compression workaround -- see line_ci_full's own
# TEXT_SCALE comment (base_charts/timeseries/line_ci_full.py) for the
# full reasoning. Must match every Base Chart's and Base Table's own
# local TEXT_SCALE, and assembly_engine.py's own CHART_RENDER_SCALE,
# exactly -- not enforced in code, per "Base Charts are outside the
# system boundary" (no shared import between this file and any Base
# Chart/Table).
#
# A Base Table is called here with width_emu/height_emu multiplied by
# this factor, same as insert_chart. Its returned chart_cells rectangle
# (Decision 28) comes back in that same inflated space, since a Base
# Table derives it proportionally from whatever width_emu/height_emu it
# was actually given -- so before that rectangle is used as a real
# slide-EMU placement offset (add_svg_picture's own left/top/width/
# height), it must be divided back down by CHART_RENDER_SCALE. The
# embedded chart's own *render* call needs no such division -- chart_rect's
# raw (undivided) width/height is already exactly CHART_RENDER_SCALE
# times the real cell size, which is exactly what a Base Chart expects
# to be called with under this same mechanism.
CHART_RENDER_SCALE = 5


def _render_chart_store_chart(ctx, chart_store_row: dict, chart_rect: dict, workfile_state):
    """
    Render one Chart Store entry's own saved chart-def, sized to
    chart_rect (a Base Table's own reserved rectangle for this cell) --
    Decisions.md: a chart embedded in a table cell is always drawn to fit
    the cell, never its own stored size. Mirrors insert_chart's own
    cache-load / cut / population-layers / render pipeline
    (assembly_engine.py) field for field, sourced from a Chart Store row
    instead of a Running Order row. Returns None on any failure -- one
    broken chart cell doesn't abort the whole table.

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

    # A blank populations field on the Chart Store entry means "inherit the
    # Running Order default" (the same inherit rule any insert_chart row
    # follows) -- ctx.default_populations is set live by a
    # set_default_populations row earlier in this same run.
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
        # An unresolvable metric_periods id no longer raises here (see
        # time_series_to_numeric_series' own docstring) — it comes
        # through as a real metric with no data. Genuinely unexpected
        # failures only now; still returns None rather than propagating,
        # per this function's own "one broken chart cell doesn't abort
        # the whole table" contract.
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
        # Every Base Table returns SVG bytes (see Architecture, SVG
        # rendering methodology) -- inserted via the shared add_svg_picture
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
