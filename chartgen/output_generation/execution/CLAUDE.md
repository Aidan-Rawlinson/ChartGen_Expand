# execution

Runs a Running Order. `batch_process` splits enabled rows by scope and iterates units. `assembly_engine.run_running_order` dispatches each row through `FUNCTION_MAP` and returns a per-run log.

A report assembles as: `create_ppt` opens the template, content rows insert into it, `save_ppt` and `save_pdf` write it out. `insert_chart` loads the shape from cache, calls `prepare_chart_cut`, calls `build_population_layers`, renders, then places the result via `add_svg_picture`.

`results.py` (`ok_result` / `err_result`) is local to this package. A row that cannot run returns an error result. It does not raise past the dispatcher, and it does not silently no-op.

`assembly_engine` is not the only module touching `python-pptx`. `insert_picture`, `insert_from_excel` and `insert_table` do too.

## Render scale

Every Base Chart and Base Table call multiplies `width_emu` and `height_emu` by `CHART_RENDER_SCALE` before rendering, and places the result at the real size. The constant is defined once, in `shared/infrastructure/render_scale.py`, and imported here and by the two preview surfaces. It must still match `TEXT_SCALE` in every Base Chart and Base Table file, which cannot import it. Full mechanism in `charts/base_charts/CLAUDE.md`.

## Render font

Every Base Chart and Base Table call is wrapped in `render_font`, from `shared/infrastructure/render_font.py`, which sets matplotlib's `font.family` to the open workfile's `default_font` setting for the duration of that render. No renderer sets a font itself.

Seven call sites, and the two table paths need two wraps each rather than one: `insert_table` renders the table, then renders each `{Cn}` chart cell in a separate pass afterwards, outside the table render's scope.

`render_font` refuses an unavailable font rather than letting matplotlib substitute one. It has to check explicitly, because matplotlib reports a missing family as a cached log record rather than a warning or an exception, and every renderer calls a blanket `warnings.filterwarnings("ignore")` at import. Reasoning in that module's own docstring.

Unlike `CHART_RENDER_SCALE`, this does reach the renderers, because `rcParams` is process-wide and they read it at draw time. It is the one rcParam ChartGen owns rather than those files.

## I/O discipline

Charts render in memory. The only disk writes during a run are the final `save_ppt` and `save_pdf` calls, one per report. The `.cgw` is read once at the start and not written again until Save.

This matters because output paths are usually OneDrive-synced. `_delete_existing_and_save` deletes any existing file at the target and confirms the deletion completed, saves, then waits for the file size to stabilise across two checks before proceeding. It raises rather than retrying indefinitely. It is not a sleep loop to be optimised away.

PowerPoint and Excel COM cleanup runs in nested `try`/`finally` blocks so each step runs regardless of what failed above it, followed by explicit `del` of the COM references. `Quit()` returning successfully does not on its own guarantee the process unloads, because `comtypes` can hold an interface pointer past the Python variable's scope.
