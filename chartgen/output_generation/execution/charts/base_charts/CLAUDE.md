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

`tweaks` is a free-text string with no structure ChartGen interprets. A chart that reads it defines its own grammar in its own file. `column_ci_full` and `line_ci_full` use `key:value^key2:value2` with a `benchmark` key, and accept `target` as a synonym for it; that is their own convention, not a system standard, and another chart may do something else.

Every chart must handle a metric with no data for some or all units.

## Adding one

Check the proposed registry key, file name and function name against `CHART_REGISTRY` and this folder first. These files arrive externally authored, so a file's own docstring or function name may be stale, or may coincidentally match an existing entry. A name match is not evidence that replacement was intended. Flag any collision and confirm before overwriting.

## Scaling: draw big, shrink on placement

PowerPoint applies a lossy compression pass over any embedded SVG. When text is kept as real `<text>` elements rather than pre-baked outline paths, that pass measurably mis-spaces individual characters. It is most visible on decimal-heavy labels, where "0.000" renders with mismatched gaps between the zeros.

The fix is to draw everything bigger, then place the result at its real size.

Every function here is called with `width_emu` and `height_emu` already multiplied by a fixed factor. It draws at that inflated size. `add_svg_picture` then places the result into the real, unmultiplied target box, scaling the SVG's content to whatever box it is given regardless of the SVG's own declared size. There is no resize-after-insert step.

### TEXT_SCALE

A bigger canvas alone is only half the mechanism. Absolute point-based sizes do not grow just because the canvas did, so left alone they render correctly against the design and far too small once the whole image is shrunk back. Each file therefore carries its own `TEXT_SCALE` and multiplies every absolute literal of that kind.

**Scale these.** Font sizes. Line widths. Marker sizes. Fixed inch or centimetre padding and offsets. Fixed font-size search bounds. Any constant expressing a physical size.

**Never scale these.** Fractions of the axes or figure. Figure-fraction and data-space coordinates. Anything in 0 to 1. Anything already derived from `width_emu` or `height_emu`. Dash-pattern lengths, for the reason below.

### Two things that look scalable and are not

**Dash patterns.** Matplotlib multiplies a dash pattern by its line's width before drawing it. The line width already carries `TEXT_SCALE`, so a typed-in `linestyle=(0, (4, 3))` comes out at the intended size on the page with no further help. Multiplying the dash lengths as well applies the factor twice and produces dashes twenty-five times too long, which reads as a nearly solid line. A dash length derived from the canvas has the opposite problem and must be divided by the line width to survive the multiplication.

**Hatching.** A matplotlib hatch repeats at a fixed rate per figure inch, so on the inflated canvas it comes out `TEXT_SCALE` times finer and shrinks to a flat wash of colour when the picture is placed. Nothing scales it: the sparsest hatch string is still five times too dense. A hatch that has to read as hatching is drawn as explicit diagonal lines at a spacing measured on the page, as in `line_ci_full`.

Every chart that draws text draws it at five times size, so PowerPoint's compression pass works on a large glyph and the error is invisible once the picture is shrunk back. There are two routes to that and no chart is exempt from it.

Most files multiply a typed-in point size by `TEXT_SCALE`. `line_ci_na` instead derives its font size from its circle radius, which derives from the canvas, so it is already inflated and a `TEXT_SCALE` would double-apply. Any size that tracks the canvas this way already carries the factor, which is why the two cannot be combined in one expression.

The single-indicator charts draw no text at all, and size their circle and mark from the canvas, so they need none.

### The value must match everywhere

Current value: **5**.

| Where | Constant |
|---|---|
| `shared/infrastructure/render_scale.py` | `CHART_RENDER_SCALE` |
| every file here that has one | `TEXT_SCALE` |

The ChartGen side has one definition, imported by every call site that inflates a render (`assembly_engine.py`, `tables/insert_table.py`, and both preview surfaces under `ui/tabs/`). Change it there and the whole ChartGen side moves together.

That is only half the job. The files here import nothing from ChartGen, by design, so each carries its own `TEXT_SCALE` literal and nothing in the code enforces that it matches. A mismatch produces incorrectly proportioned text and lines in that one file only, with no error anywhere. Changing the value means changing it in `render_scale.py` and in every file here.

`svg.fonttype` is `"none"` in every file here. No exceptions.

## rcParams are global, and every file here gets imported

`registry.py` imports all of these modules, and `base_charts/__init__.py` imports the registry, so importing any one chart runs the module-level code of all of them. Matplotlib's `rcParams` is a single process-wide object.

A setting assigned at module level therefore does not belong to the file that assigns it. It belongs to whichever file imported last. That is harmless while every file sets the same value, which is why `svg.fonttype` can stay where it is.

The moment one file wants a different value, an import-time assignment silently loses. Any file needing an rcParam the others do not share has to set it inside `matplotlib.rc_context` in the chart function, so it applies to that render and to nothing else.

## The font is not set here

**No file here sets `font.family`.** Not at module level, not in an `rc_context`, not as `fontname=` or `FontProperties(family=...)`. Nothing names a typeface anywhere in this folder.

The font is a stored user choice, held in the open workfile's settings and set on the Settings tab. ChartGen applies it around every render call, through `shared/infrastructure/render_font.py`, at all seven call sites. These files inherit it.

That is the one rcParam ChartGen owns rather than these files. It is also the reason the rule above stops being theoretical: this folder used to carry 32 module-level assignments of `font.family`, and the two files that wanted a different value from the rest had to reach for `rc_context` to get it. Now nobody sets it and the question does not arise.

A file that reintroduces one does not merely differ, it overrides the user's choice for that one chart and silently reverts a setting they made deliberately. These files arrive externally authored and an author testing one standalone will see matplotlib's default font, so the temptation to "fix" it by adding a family is real. The contract handed out with the download bundle says not to (`custom_charts/contract.py`). Check for it when a file comes back.

### Measuring text is measuring a font

A chart that reserves space by drawing a string and reading its width back is measuring whatever font is in force at that moment. Do that inside the chart function.

At module level the font is not yet known: these modules are imported when the application starts, long before a workfile is open, so a width computed there is measured against matplotlib's default and no later render can correct it. `sparkline2` and `sparkline3` reserve a fixed-width label section this way and compute it per call, in `_hasdata_section_width_in` and `_right_label_width_in`, for exactly this reason. The same string spans about 2.9in in Calibri against 3.5in in matplotlib's default at those sizes, and the whole point of the reserved section is to keep a column of these charts aligned.

The four grid and card tables in `base_tables/` fit their font size by measuring the same way, inside their render, so they adapt to the font on their own.

### Weights come from separate font files

Matplotlib picks a face per element from the weight and style asked for, which means a family only has bold if a bold face is registered for it. A family shipped as one variable font file has just its default instance, matplotlib cannot walk the weight axis, and `fontweight="bold"` silently comes back at regular weight. `bundled_fonts.has_bold_face` reports this and the Settings tab warns about it, so it is visible rather than discovered in a finished report — but a chart drawing bold text is relying on the bundled fonts including a bold face.
