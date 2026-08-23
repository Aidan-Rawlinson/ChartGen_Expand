"""
batch_process.py
Owns the batch loop that runs a Running Order across multiple reporting units.
Splits enabled rows by scope (batch_open / normal / batch_close), runs any
batch_open rows once, runs the normal rows once per unit via
assembly_engine.run_running_order against a shared AssemblyContext, then runs
any batch_close rows once. assembly_engine remains the module that knows how
to execute a single report's rows; this module is purely about iteration
across units for Run Selected / Run Batch / Run All.

A batch_open or batch_close row that fails is reported as its own run-log
entry, in the same shape as a per-unit one, since it has no unit of its
own to be attributed to.
"""

import os
import time

from chartgen.output_generation.execution.assembly_engine import (
    run_running_order, AssemblyContext, FUNCTION_MAP
)


def _run_batch_scope_row(row: dict, shared_ctx, base_settings: dict) -> dict:
    """
    Run one batch_open or batch_close row and report the outcome the same
    way a per-unit report does, or None if it succeeded.

    These rows (open_excel, close_excel) run once per batch rather than
    once per unit, so they have no unit of their own to be logged against.
    Their failures were previously discarded entirely, which left a failed
    open_excel to surface only indirectly, as every later insert_from_excel
    row reporting "workbook is not open" with the real cause thrown away,
    and a failed close_excel to surface not at all, despite leaving an
    Excel process behind. Same six keys as a per-unit entry, so the run
    log and the error count both pick these up unchanged.
    """
    func = FUNCTION_MAP.get(str(row.get("function", "")).strip())
    if not func:
        return None

    function_name = str(row.get("function", "")).strip()
    try:
        result = func(shared_ctx, row, base_settings)
    except Exception as e:
        message = f"{type(e).__name__}: {e}"
    else:
        # A row that cannot run returns an error result rather than raising.
        if not isinstance(result, dict) or result.get("status") == "ok":
            return None
        message = result.get("message", "Unknown error")

    return {
        "idx":     "",
        "code":    function_name,
        "name":    f"Row {row.get('row_id', '?')}",
        "ok":      False,
        "elapsed": 0.0,
        "error":   message,
    }


def run_batch(rows: list, units_to_run: list, all_units: list,
               base_settings: dict, on_unit_complete=None) -> dict:
    """
    Execute rows across units_to_run.

    rows             - enabled Running Order rows (any scope)
    units_to_run     - the unit dicts to process this run, in order
    all_units        - the full population, used only to number units_to_run
                        against their position in the overall queue
    base_settings    - settings dict (cleaned_template_path, outputs_folder,
                        workfile_state, etc.); per-unit overrides are layered
                        onto a copy, base_settings itself is not mutated
    on_unit_complete - optional callback(log_entry: dict) invoked after each
                        unit completes, for UI progress reporting

    Returns {"ok_count": int, "err_count": int, "elapsed": float, "log_rows": list[dict]}
    """
    batch_open  = [r for r in rows if str(r.get("scope", "normal")).strip() == "batch_open"]
    normal_rows = [r for r in rows if str(r.get("scope", "normal")).strip() == "normal"]
    batch_close = [r for r in rows if str(r.get("scope", "normal")).strip() == "batch_close"]

    t_overall = time.perf_counter()
    log_rows = []

    shared_ctx = AssemblyContext()
    outputs_dir = base_settings.get("outputs_folder", "")
    if outputs_dir:
        os.makedirs(os.path.join(outputs_dir, "pptx"), exist_ok=True)
        os.makedirs(os.path.join(outputs_dir, "pdf"), exist_ok=True)

    for row in batch_open:
        failure = _run_batch_scope_row(row, shared_ctx, base_settings)
        if failure:
            log_rows.append(failure)
            if on_unit_complete:
                on_unit_complete(failure)

    for idx, unit in enumerate(units_to_run):
        pop_idx = next((i + 1 for i, s in enumerate(all_units)
                        if str(s["unit_id"]) == str(unit["unit_id"])), idx + 1)

        run_settings = dict(base_settings)
        run_settings["reporting_unit_name"] = unit["unit_code"]
        run_settings["selected_unit_id"]    = str(unit["unit_id"])

        result = run_running_order(normal_rows, run_settings, ctx=shared_ctx)

        err_msg = ""
        if result["status"] != "ok":
            errs = [e for e in result["log"] if e["status"] == "error"]
            if errs:
                first = errs[0]
                err_msg = f"Row {first.get('row_id', '?')}: {first['message']}"
            else:
                err_msg = "Unknown error"

        log_entry = {
            "idx":     pop_idx,
            "code":    unit["unit_code"],
            "name":    unit["unit_name"],
            "ok":      result["status"] == "ok",
            "elapsed": result["elapsed"],
            "error":   err_msg,
        }
        log_rows.append(log_entry)
        if on_unit_complete:
            on_unit_complete(log_entry)

    for row in batch_close:
        failure = _run_batch_scope_row(row, shared_ctx, base_settings)
        if failure:
            log_rows.append(failure)
            if on_unit_complete:
                on_unit_complete(failure)

    elapsed_total = time.perf_counter() - t_overall
    ok_count  = sum(1 for r in log_rows if r["ok"])
    err_count = len(log_rows) - ok_count

    return {"ok_count": ok_count, "err_count": err_count, "elapsed": elapsed_total, "log_rows": log_rows}
