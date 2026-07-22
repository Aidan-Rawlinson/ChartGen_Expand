"""
assembly_engine.py
Executes a Running Order's normal-scope rows against an open PowerPoint
template to produce one report. Dispatches each row to its Running Order
function (create_ppt, insert_chart, insert_picture, insert_from_excel,
update_text, save_ppt, etc) via FUNCTION_MAP and returns a per-run log.

Note (Restructure_Plan.md Open Item 1): this module was previously described
as "the only package touching python-pptx directly" — that is no longer
true now insert_picture and insert_from_excel also manipulate python-pptx
objects. Its actual purpose is dispatch/execution of one report's Running
Order rows, not exclusive ownership of python-pptx.
"""

import os
import time
import traceback
from dataclasses import replace

from pptx import Presentation
from pptx.util import Emu

from core.output_generation.execution.charts.cache_reader import load_shape
from core.output_generation.execution.charts.base_charts import render_chart
from core.output_generation.execution.text.text_engine import update_text
from core.shared.infrastructure.report_context import build_report_context
from core.shared.infrastructure.soft_parents import resolve_full_unit_set
from core.shared.normalisation_containers.population_layers import build_population_layers
from core.shared.normalisation_containers.shapes import apply_period_range
from core.shared.normalisation_containers.shape_transforms import maybe_convert_periods_to_metrics
from core.output_generation.definition.running_order.dialog_support import parse_metric_periods_string
from core.output_generation.execution.pictures.insert_picture import insert_picture
from core.output_generation.execution.excel.insert_from_excel import (
    open_excel, close_excel, insert_from_excel
)
from core.output_generation.execution.results import ok_result, err_result
from core.workfile.state.workfile_file import master_table_rows


# ---------------------------------------------------------------------------
# Assembly context — passed through every function call in a run
# ---------------------------------------------------------------------------

class AssemblyContext:
    def __init__(self):
        self.prs: Presentation = None
        self.output_path: str = ""
        self.template_path: str = ""
        self.log: list[dict] = []
        self.autotable_stats: dict = {}
        self.report_context = None      # set by run_running_order
        self.full_unit_set: dict = {}   # {table_name: [row, ...]} for the current reporting unit, set by run_running_order
        self.default_populations: str = ""  # set by set_default_populations row


# ---------------------------------------------------------------------------
# Running Order function implementations
# ---------------------------------------------------------------------------

def create_ppt(ctx: AssemblyContext, row: dict, settings: dict) -> dict:
    """
    Open the cleaned template and set the output path.
    Does not write to disk — save_ppt/save_pdf do that.
    """
    template_path = settings.get("cleaned_template_path", "").strip()
    if not template_path or not os.path.exists(template_path):
        # Fall back to the original template if no cleaned version exists
        template_path = settings.get("ppt_template_path", "").strip()

    if not template_path or not os.path.exists(template_path):
        return err_result(row, "create_ppt: no template found. Check settings.")

    output_folder = _ensure_output_folder(settings)
    unit_name = (settings.get("reporting_unit_name") or "").strip()
    if not unit_name:
        unit_name = str(settings.get("selected_unit_id") or "output").strip()
    safe_name = _safe_filename(unit_name)
    output_path = os.path.join(output_folder, "pptx", f"{safe_name}.pptx")

    ctx.prs = Presentation(template_path)
    ctx.output_path = output_path
    ctx.template_path = template_path

    return ok_result(row, f"Template opened: {os.path.basename(template_path)}")


def set_default_populations(ctx: AssemblyContext, row: dict, settings: dict) -> dict:
    """
    Store the default populations string on AssemblyContext.
    Subsequent insert_chart rows inherit it unless overridden per row.
    """
    populations = str(row.get("populations", "") or "").strip()
    ctx.default_populations = populations
    return ok_result(row, f"Default populations set: '{populations}'")


def insert_chart(ctx: AssemblyContext, row: dict, settings: dict) -> dict:
    """Render a Base Chart from cached data and insert it at the row's position."""
    if ctx.prs is None:
        return err_result(row, "insert_chart: no open presentation (create_ppt not called?).")

    cache_file = str(row.get("cache_file") or "").strip()
    if cache_file.lower() == "none":
        cache_file = ""
    chart_type_ref = str(row.get("chart_type_ref", "")).strip()
    slide_index = _int_or_none(row.get("slide_index"))

    # Position / size from the Running Order row (written from template at generation time)
    left_emu = _int_or_none(row.get("left_emu"))
    top_emu = _int_or_none(row.get("top_emu"))
    width_emu = _int_or_none(row.get("width_emu"))
    height_emu = _int_or_none(row.get("height_emu"))

    # Validate required fields
    missing = []
    if not cache_file:  missing.append("cache_file")
    if not chart_type_ref: missing.append("chart_type_ref")
    if slide_index is None: missing.append("slide_index")
    if None in (left_emu, top_emu, width_emu, height_emu):
        missing.append("position/size EMU values")
    if missing:
        return err_result(row, f"insert_chart: missing required fields: {', '.join(missing)}")

    # --- Resolve populations for this chart ---
    row_populations = str(row.get("populations", "") or "").strip()
    populations_str = row_populations if row_populations else ctx.default_populations

    render_context = ctx.report_context

    # --- Load data shape ---
    try:
        data_shape, shape_type = _load_chart_data(cache_file, settings.get("workfile_state"))
    except Exception as e:
        return err_result(row, f"insert_chart: failed to load cache '{cache_file}': {e}")

    # --- Trim to the row's period range (TimeSeries only; no-op otherwise) ---
    # A normalisation step at the boundary, ahead of population-layer
    # filtering, so the charting side sees a shape that already only spans
    # the periods in scope — nothing downstream needs to know a range was
    # ever set (Functional Spec §10.4 filters units the same way).
    start_period = str(row.get("start_period", "") or "").strip()
    end_period = str(row.get("end_period", "") or "").strip()
    if start_period or end_period:
        data_shape = apply_period_range(data_shape, start_period, end_period)

    # --- Convert selected periods into a metric snapshot (TimeSeries only;
    # no-op if metric_periods is blank). Applied after the range trim, so a
    # metric_periods id that fell outside a start_period/end_period range on
    # the same row correctly surfaces as the same "not found" error below,
    # rather than silently succeeding against the untrimmed shape. ---
    metric_period_ids = parse_metric_periods_string(str(row.get("metric_periods", "") or ""))
    if metric_period_ids:
        try:
            data_shape = maybe_convert_periods_to_metrics(data_shape, metric_period_ids)
        except ValueError as e:
            return err_result(row, f"insert_chart: metric_periods conversion failed: {e}")

    # --- Build population layers ---
    population_layers = []
    if render_context is not None and populations_str:
        workfile_state = settings.get("workfile_state")
        # A chart's population lives in whichever table its data shape names
        # (population_table) — not necessarily the current master table.
        # Falls back to master for legacy cached data fetched before
        # population_table existed.
        target_table = data_shape.population_table or (
            workfile_state.table_order[0] if workfile_state.table_order else ""
        )
        target_rows = workfile_state.tables.get(target_table, [])
        # Selected can legitimately be more than one unit in this table —
        # e.g. an organisation supporting two ICBs highlights both ICBs on
        # an ICB-level chart. ctx.full_unit_set already resolved this per
        # table for the current reporting unit; just look up its table.
        selected_ids = {r["unit_id"] for r in ctx.full_unit_set.get(target_table, [])}
        try:
            population_layers = build_population_layers(
                data_shape, populations_str, target_rows, selected_ids
            )
        except Exception as e:
            return err_result(row, f"insert_chart: failed to build population layers: {e}")

    # Fall back to full unfiltered shape if no populations resolved
    if not population_layers:
        population_layers = [replace(data_shape, population_label="All")]

    # --- Render chart image ---
    try:
        image_bytes, autotable_stats = _render_chart_image(
            chart_type_ref, population_layers, width_emu, height_emu, render_context
        )
    except Exception as e:
        return err_result(row, f"insert_chart: render failed for '{chart_type_ref}': {e}")

    # Store autotable stats keyed by row_id — placeholder name is only
    # unique per slide, not across the whole Running Order, so it can't be
    # used as a key here (two slides may both have a placeholder named
    # "Chart 1"). row_id is the row's real identity (Architecture Decision 11).
    ctx.autotable_stats[row.get("row_id")] = autotable_stats

    # --- Insert into slide ---
    try:
        _insert_image_at_position(
            ctx.prs, slide_index,
            image_bytes, left_emu, top_emu, width_emu, height_emu
        )
    except Exception as e:
        return err_result(row, f"insert_chart: failed to insert image on slide {slide_index}: {e}")

    return ok_result(row, f"Chart '{chart_type_ref}' inserted (slide {slide_index + 1})")


def empty_placeholder(ctx: AssemblyContext, row: dict, settings: dict) -> dict:
    """No-op. Placeholder has no content assigned."""
    return ok_result(row, f"empty_placeholder: row {row.get('row_id')} skipped (no content assigned)")


def save_ppt(ctx: AssemblyContext, row: dict, settings: dict) -> dict:
    """Save the completed output as a .pptx file."""
    if ctx.prs is None:
        return err_result(row, "save_ppt: no open presentation.")
    try:
        os.makedirs(os.path.dirname(ctx.output_path), exist_ok=True)
        ctx.prs.save(ctx.output_path)
        return ok_result(row, f"Saved: {ctx.output_path}")
    except Exception as e:
        return err_result(row, f"save_ppt: {e}")


def save_pdf(ctx: AssemblyContext, row: dict, settings: dict) -> dict:
    """
    Save the completed output as a .pdf using COM automation (Windows/PowerPoint only).
    Falls back gracefully on non-Windows or if PowerPoint is not available.
    """
    if ctx.prs is None:
        return err_result(row, "save_pdf: no open presentation.")

    pdf_dir = os.path.join(os.path.dirname(os.path.dirname(ctx.output_path)), "pdf")
    pdf_path = os.path.join(pdf_dir, os.path.basename(ctx.output_path).replace(".pptx", ".pdf"))
    os.makedirs(pdf_dir, exist_ok=True)

    # Ensure the pptx is saved first (COM needs a file on disk to open)
    try:
        ctx.prs.save(ctx.output_path)
    except Exception as e:
        return err_result(row, f"save_pdf: could not save .pptx before PDF export: {e}")

    try:
        import comtypes.client
        powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
        powerpoint.Visible = 1
        deck = powerpoint.Presentations.Open(os.path.abspath(ctx.output_path))
        deck.ExportAsFixedFormat(
                os.path.abspath(pdf_path),
                2,   # ppFixedFormatTypePDF
                2,   # Intent: ppFixedFormatIntentPrint (vs 1 = screen quality)
            )
        deck.Close()
        powerpoint.Quit()
        return ok_result(row, f"PDF saved: {pdf_path}")
    except ImportError:
        return err_result(row, "save_pdf: comtypes not available — PDF export requires Windows + PowerPoint.")
    except Exception as e:
        return err_result(row, f"save_pdf: COM export failed: {e}")


# ---------------------------------------------------------------------------
# Dispatch map  —  function name -> callable
# ---------------------------------------------------------------------------

FUNCTION_MAP = {
    "create_ppt":               create_ppt,
    "set_default_populations":  set_default_populations,
    "insert_chart":             insert_chart,
    "insert_picture":           insert_picture,
    "insert_from_excel":        insert_from_excel,
    "open_excel":               open_excel,
    "close_excel":              close_excel,
    "update_text":              update_text,
    "empty_placeholder":        empty_placeholder,
    "save_ppt":                 save_ppt,
    "save_pdf":                 save_pdf,
}


# ---------------------------------------------------------------------------
# Run a complete Running Order
# ---------------------------------------------------------------------------

def run_running_order(rows: list[dict], settings: dict,
                      ctx: AssemblyContext = None) -> dict:
    """
    Execute a list of Running Order rows (already filtered to enabled only).

    settings dict must contain at minimum:
      ppt_template_path, cleaned_template_path, workfile_folder,
      reporting_unit_name, workfile_state

    Returns:
    {"status": "ok" | "error", "output_path": str, "elapsed": float, "log": list[dict]}
    """
    # Use a shared context if provided (batch run), otherwise create a fresh one.
    if ctx is None:
        ctx = AssemblyContext()

    workfile_state = settings.get("workfile_state")
    units = master_table_rows(workfile_state)
    ctx.report_context = build_report_context(settings, units)

    master_table_name = workfile_state.table_order[0] if workfile_state.table_order else ""
    reporting_row = None
    if ctx.report_context is not None:
        reporting_row = next(
            (r for r in units if str(r["unit_id"]) == ctx.report_context.unit_id), None
        )
    ctx.full_unit_set = (
        resolve_full_unit_set(reporting_row, master_table_name, workfile_state.tables)
        if reporting_row is not None else {}
    )

    t_start = time.perf_counter()

    normal_rows = [r for r in rows if str(r.get("scope", "normal")).strip() == "normal"]
    rows_to_run = normal_rows

    for i, row in enumerate(rows_to_run):
        func_name = str(row.get("function", "")).strip()

        func = FUNCTION_MAP.get(func_name)
        if func is None:
            result = err_result(row, f"Unknown function: '{func_name}'")
        else:
            try:
                result = func(ctx, row, settings)
            except Exception as e:
                result = err_result(row, f"Unhandled exception in '{func_name}': {traceback.format_exc()}")

        ctx.log.append(result)

        # Abort on error in structural functions
        if result["status"] == "error" and func_name in ("create_ppt",):
            ctx.log.append({"status": "aborted",
                            "message": "Batch aborted after create_ppt failure."})
            break

    elapsed = time.perf_counter() - t_start
    overall_status = "ok" if all(r["status"] in ("ok", "skip") for r in ctx.log) else "error"

    return {
        "status": overall_status,
        "output_path": ctx.output_path,
        "elapsed": elapsed,
        "log": ctx.log,
    }


# ---------------------------------------------------------------------------
# Private helpers — internal to insert_chart sub-steps
# ---------------------------------------------------------------------------

def _load_chart_data(cache_file: str, workfile_state=None):
    """Load a canonical data shape from the cache. Sub-step of insert_chart."""
    return load_shape(cache_file, workfile_state)


def _render_chart_image(chart_type_ref: str, population_layers: list, width_emu: int, height_emu: int,
                        report_context=None):
    """
    Render a Matplotlib chart to PNG bytes sized to the placeholder.
    Sub-step of insert_chart.
    """
    NARROWER_EMU = 6858000
    width_pct  = max(10, int(min(100, (width_emu  / NARROWER_EMU) * 100)))
    height_pct = max(10, int(min(100, (height_emu / NARROWER_EMU) * 100)))

    image_bytes, autotable_stats = render_chart(
        chart_type_ref, population_layers,
        width=width_pct, height=height_pct,
        report_context=report_context,
    )
    return image_bytes, autotable_stats


def _insert_image_at_position(prs: Presentation, slide_index: int,
                               image_bytes, left_emu: int, top_emu: int,
                               width_emu: int, height_emu: int):
    """
    Insert a PNG image at the exact EMU position on the given slide.
    Sub-step of insert_chart.
    """
    if slide_index >= len(prs.slides):
        raise IndexError(
            f"Slide index {slide_index} out of range "
            f"(template has {len(prs.slides)} slides)."
        )
    slide = prs.slides[slide_index]
    image_bytes.seek(0)
    slide.shapes.add_picture(
        image_bytes,
        Emu(left_emu), Emu(top_emu),
        Emu(width_emu), Emu(height_emu),
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _ensure_output_folder(settings: dict) -> str:
    output_folder = settings.get("outputs_folder", "").strip()
    if not output_folder:
        workfile_folder = settings.get("workfile_folder", "").strip()
        output_folder = os.path.join(workfile_folder, "outputs") if workfile_folder else "outputs"
    os.makedirs(output_folder, exist_ok=True)
    return output_folder


def _safe_filename(name: str) -> str:
    """Strip characters that are unsafe in filenames."""
    import re
    safe = re.sub(r'[\\/:*?"<>|]', "_", name)
    return safe.strip("_") or "output"


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
