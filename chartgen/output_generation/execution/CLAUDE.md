# execution

Runs a Running Order. `batch_process` splits enabled rows by scope and iterates units. `assembly_engine.run_running_order` dispatches each row through `FUNCTION_MAP` and returns a per-run log.

A report assembles as: `create_ppt` opens the template, content rows insert into it, `save_ppt` and `save_pdf` write it out. `insert_chart` loads the shape from cache, calls `prepare_chart_cut`, calls `build_population_layers`, renders, then places the result via `add_svg_picture`.

`results.py` (`ok_result` / `err_result`) is local to this package. A row that cannot run returns an error result. It does not raise past the dispatcher, and it does not silently no-op.

`assembly_engine` is not the only module touching `python-pptx`. `insert_picture`, `insert_from_excel` and `insert_table` do too.

## Render scale

Every Base Chart and Base Table call multiplies `width_emu` and `height_emu` by `CHART_RENDER_SCALE` before rendering, and places the result at the real size. The constant is duplicated at four call sites and must match `TEXT_SCALE` in every Base Chart and Base Table file. Full mechanism in `charts/base_charts/CLAUDE.md`.

## I/O discipline

Charts render in memory. The only disk writes during a run are the final `save_ppt` and `save_pdf` calls, one per report. The `.cgw` is read once at the start and not written again until Save.

This matters because output paths are usually OneDrive-synced. `_delete_existing_and_save` deletes any existing file at the target and confirms the deletion completed, saves, then waits for the file size to stabilise across two checks before proceeding. It raises rather than retrying indefinitely. It is not a sleep loop to be optimised away.

PowerPoint and Excel COM cleanup runs in nested `try`/`finally` blocks so each step runs regardless of what failed above it, followed by explicit `del` of the COM references. `Quit()` returning successfully does not on its own guarantee the process unloads, because `comtypes` can hold an interface pointer past the Python variable's scope.
