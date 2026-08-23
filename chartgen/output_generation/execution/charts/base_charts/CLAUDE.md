# base_charts

The built-in Base Charts, one folder per canonical data shape. Dispatch in `registry.py`.

## These files are outside the system boundary

A Base Chart is a rendering artefact, like a `.crtx` chart template. Not application logic.

One standalone file per `base_chart_name`. Each carries its own copy of whatever helpers it needs and imports nothing from ChartGen. There is no shared helpers module and there must not be one.

**Do not refactor, deduplicate, or extract common code from these files.** The repetition is the design. Self-containment is what makes a file safe to hand whole to an external AI for editing and paste back.

## chart_inputs

```
f(population_layers, width_emu, height_emu, tweaks) -> image_bytes
```

Nothing else is passed in. No `report_context`, no `AssemblyContext`, no workfile state.

Returns image bytes only. A Base Chart does not compute, return or relay statistics. Those are a property of the data shape, and a caller that needs them already holds `population_layers` and calls `summary_stats_by_layer` or `units_by_layer` directly.

Selected-unit identity is read from the `"Selected"`-labelled entry in `population_layers`.

`tweaks` is a free-text string with no structure ChartGen interprets. A chart that reads it defines its own grammar in its own file. `column_ci_full` and `line_ci_full` use `key:value^key2:value2` with a `target` key; that is their own convention, not a system standard, and another chart may do something else.

Every chart must handle a metric with no data for some or all units.

## Adding one

Check the proposed registry key, file name and function name against `CHART_REGISTRY` and this folder first. These files arrive externally authored, so a file's own docstring or function name may be stale, or may coincidentally match an existing entry. A name match is not evidence that replacement was intended. Flag any collision and confirm before overwriting.

## Scaling: draw big, shrink on placement

PowerPoint applies a lossy compression pass over any embedded SVG. When text is kept as real `<text>` elements rather than pre-baked outline paths, that pass measurably mis-spaces individual characters. It is most visible on decimal-heavy labels, where "0.000" renders with mismatched gaps between the zeros.

The fix is to draw everything bigger, then place the result at its real size.

Every function here is called with `width_emu` and `height_emu` already multiplied by a fixed factor. It draws at that inflated size. `add_svg_picture` then places the result into the real, unmultiplied target box, scaling the SVG's content to whatever box it is given regardless of the SVG's own declared size. There is no resize-after-insert step.

### TEXT_SCALE

A bigger canvas alone is only half the mechanism. Absolute point-based sizes do not grow just because the canvas did, so left alone they render correctly against the design and far too small once the whole image is shrunk back. Each file therefore carries its own `TEXT_SCALE` and multiplies every absolute literal of that kind.

**Scale these.** Font sizes. Line widths. Marker sizes. Dash-pattern lengths. Fixed inch padding and offsets. Fixed font-size search bounds. Any constant expressing a physical size.

**Never scale these.** Fractions of the axes or figure. Figure-fraction and data-space coordinates. Anything in 0 to 1. Anything already derived from `width_emu` or `height_emu`.

Every chart that draws text draws it at five times size, so PowerPoint's compression pass works on a large glyph and the error is invisible once the picture is shrunk back. There are two routes to that and no chart is exempt from it.

Most files multiply a typed-in point size by `TEXT_SCALE`. `line_ci_na` instead derives its font size from its circle radius, which derives from the canvas, so it is already inflated and a `TEXT_SCALE` would double-apply. Any size that tracks the canvas this way already carries the factor, which is why the two cannot be combined in one expression.

The single-indicator charts draw no text at all, and size their circle and mark from the canvas, so they need none.

### The value must match everywhere

Current value: **5**.

| Where | Constant |
|---|---|
| `output_generation/execution/assembly_engine.py` | `CHART_RENDER_SCALE` |
| `output_generation/execution/tables/insert_table.py` | `CHART_RENDER_SCALE` |
| `ui/tabs/charts_tab.py` | `CHART_RENDER_SCALE` |
| `ui/tabs/output_tables_tab.py` | `CHART_RENDER_SCALE` |
| every file here that has one | `TEXT_SCALE` |

Nothing in the code enforces this. These files import nothing from ChartGen, by design, so there is no shared constant to import. A mismatch produces incorrectly proportioned text and lines in that one file only, with no error anywhere. Change the value in one place and it has to change in all of them.

`svg.fonttype` is `"none"` in every file here. No exceptions. Font is Calibri, set per file.
