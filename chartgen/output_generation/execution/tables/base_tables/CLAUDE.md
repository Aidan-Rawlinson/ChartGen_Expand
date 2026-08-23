# base_tables

The built-in Base Tables: `plain_grid`, `table_cardtile`, and their two-row-header CI-report variants `ci_grid` and `ci_cardtile`. Dispatch in `registry.py`.

## These files are outside the system boundary

A Base Table is a rendering artefact, not application logic. One standalone file per `table_type_ref`, each carrying its own copy of whatever helpers it needs, importing nothing from ChartGen. There is no shared helpers module and there must not be one.

**Do not refactor, deduplicate, or extract common code from these files.** The repetition is the design.

A Base Table is not scoped to a data shape. Every one takes the same already-resolved grid, so a saved Custom Table is a valid option everywhere the moment it is saved.

## table_inputs

```
f(content, column_widths, row_heights, width_emu, height_emu, tweaks)
    -> (image_bytes, chart_cells)
```

`content` arrives already resolved: Stat Tags substituted, `<br>` converted to a real newline. A Base Table only ever sees a genuine newline character, which matplotlib stacks natively.

`chart_cells` is `{tag: {"x", "y", "width", "height"}}`, all four in EMU, one entry per chart-component cell found. A style that finds none returns `{}`.

A chart-component cell is recognised by a plain string check: starts `{`, ends `}`, first inner character is `C`. Nothing about what follows is checked, so hand-typed ids such as `{CH1}` are valid.

A style supporting line breaks needs a height-aware font fit, not just the width-based fit. Checking a multi-line cell's real rendered height against its row's available height, and shrinking further if needed, is what keeps the extra lines visible rather than merely present in the file.

## What "the cell" means

The rectangle a style reports is a design decision, not a geometry lookup. Padding, borders, drop shadows and rounded corners can all mean the reported rectangle is deliberately smaller than the raw `column_widths` and `row_heights` cell. `table_cardtile` insets its card from its row; its header row, having no card, reports the raw cell. Rounded corners report the plain bounding box, because a placed picture is rectangular regardless.

## The bbox_inches trap

A style whose `savefig` uses `bbox_inches="tight"`, which anything drawing deliberately outside its axes needs, cannot assume its 0 to 100 data axis maps 1:1 onto its declared canvas. The crop expands or shrinks the saved image asymmetrically depending on what actually bled out, and a chart-cell rectangle computed as a naive fraction of the nominal canvas drifts out of alignment.

Two fixes, for two situations.

**Nothing drawn outside the axes.** Drop `bbox_inches="tight"` entirely and make the axes fill the figure explicitly with `fig.add_axes([0, 0, 1, 1])` rather than `tight_layout`. The 0 to 100 space then maps onto the declared canvas exactly, with nothing to correct afterwards. This is `plain_grid`. Prefer it whenever it applies.

**Deliberate overflow needed.** Keep `bbox_inches="tight"` and call `fig.get_tightbbox(renderer)` once all drawing is complete, then remap every cell's data-space coordinates through the actual crop bounding box plus `pad_inches` before converting to EMU. This is `table_cardtile`, the reference implementation for any new style needing overflow.

## Scaling: draw big, shrink on placement

PowerPoint applies a lossy compression pass over any embedded SVG. When text is kept as real `<text>` elements rather than pre-baked outline paths, that pass measurably mis-spaces individual characters. It is most visible on decimal-heavy labels, where "0.000" renders with mismatched gaps between the zeros.

The fix is to draw everything bigger, then place the result at its real size.

Every function here is called with `width_emu` and `height_emu` already multiplied by a fixed factor. It draws at that inflated size. `add_svg_picture` then places the result into the real, unmultiplied target box, scaling the SVG's content to whatever box it is given regardless of the SVG's own declared size. There is no resize-after-insert step.

**`chart_cells` comes back in inflated space.** The rectangle is derived proportionally from whatever `width_emu` and `height_emu` this function was given, so it is already inflated. The embedded chart's own render call uses the rectangle raw, which is correct. Placing the resulting picture divides by the factor first. Divide at the placement boundary only, never at the render boundary.

### TEXT_SCALE

A bigger canvas alone is only half the mechanism. Absolute point-based sizes do not grow just because the canvas did, so left alone they render correctly against the design and far too small once the whole image is shrunk back. Each file therefore carries its own `TEXT_SCALE` and multiplies every absolute literal of that kind.

**Scale these.** Font sizes. Line widths. Marker sizes. Dash-pattern lengths. Fixed inch padding and offsets. Fixed font-size search bounds. Any constant expressing a physical size.

**Never scale these.** Fractions of the axes or figure. Figure-fraction and data-space coordinates. Anything in 0 to 1. Anything already derived from `width_emu` or `height_emu`.

### The value must match everywhere

Current value: **5**.

| Where | Constant |
|---|---|
| `shared/infrastructure/render_scale.py` | `CHART_RENDER_SCALE` |
| every file here | `TEXT_SCALE` |

The ChartGen side has one definition, imported by every call site that inflates a render (`assembly_engine.py`, `tables/insert_table.py`, and both preview surfaces under `ui/tabs/`). Change it there and the whole ChartGen side moves together.

That is only half the job. The files here import nothing from ChartGen, by design, so each carries its own `TEXT_SCALE` literal and nothing in the code enforces that it matches. A mismatch produces incorrectly proportioned text and lines in that one file only, with no error anywhere. Changing the value means changing it in `render_scale.py` and in every file here.

`svg.fonttype` is `"none"` in every file here. No exceptions. Font is Calibri, set per file. `DPI = 300` is used only for matplotlib's own text-metric estimation during layout and has no bearing on the SVG's resolution.
