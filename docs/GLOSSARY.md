# ChartGen - Glossary

The terms used consistently across the codebase and the other documents.

Formats and schemas are in [DATA_FORMATS.md](DATA_FORMATS.md). Structure is in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Python vocabulary

Not ChartGen-specific. Here so the same words mean the same thing in discussion.

| Term | Means |
|---|---|
| Package | A folder with `__init__.py` |
| Directory | A folder without `__init__.py` |
| Sub-package | A package nested inside another |
| Module | A `.py` file |

---

## Benchmarking domain

**Normalisation** - bringing data from different sources into a single consistent structure and format.

**Population** - the set of units being compared. One output may include several populations, usually in a hierarchical relationship, for example Regions, Organisations and Emergency Departments.

**Unit** - a single organisation or entity compared against others within a population. Often but not always matches a project submission.

**Reporting unit** - the unit an output is being generated for. A named special case of Unit.

**Selected unit** - the unit or units that are the current focus of an analysis, examined against the wider population. May be the reporting unit but does not have to be. A report for an organisation can hold a chart where an Emergency Department is the selected unit.

**Peer group** - a named subset of the population, defined by a `Name()` column such as `Region()` or `Shelford Group()`. A unit with no group for that column is marked `x` or left blank rather than assigned one.

**Summary statistics** - numeric values describing a population's data: mean, median, quartiles, peer averages.

**Project** - a single benchmarking exercise with its own data collection, population and reporting cycle, identified by a `project_id` and `year`. TBN uses "project", not "programme", for this.

**Output** - a generated PowerPoint or PDF deliverable. Preferred over "report", since it also covers slide packs, fliers and presentations.

**Individualised Report** - fixed structure, data varying per instance.

**Algorithmic Report** - structure itself varying per unit through conditional logic, not just the data within a fixed structure.

**Bespoke Narrative** - per-unit written narrative, whether looked up, algorithmically selected, AI generated, or a combination.

---

## Toolkit structures

**NHS toolkit** - the first data source. Chart URLs classified `database = "nhs"`.

**Indicators toolkit** - the second data source, timeseries data. A different API host and URL shape. Chart URLs classified `database = "indicators"`.

**Tier** - a component of the toolkit structure that hosts charts.

**Service** - part of the project process allowing several questionnaires per project. A URL component.

**Denominator** - a URL component letting one page carry several data sources or calculations. Most often varies the denominator, but can change numerators and calculations too.

**Period** (`period_id`, `period_label`) - a single point on a TimeSeries shape's period axis, shared across every Metric-Series in that shape. Numbering is per report: the same calendar month can be a different `period_id` in two different reports.

---

## Files and sessions

**`.cgw`** - ChartGen Workfile. A ZIP holding one workfile's complete saved state.

**Data Cache** - the on-disk store of fetched chart data: `manifest.csv` plus one JSON per chart. Mirrored in memory by `WorkfileState.cache` and `.manifest_rows`.

**Manifest table** (`manifest.csv`) - the chart URL table, and the canonical index of every chart in a workfile. One row per URL.

**Hex id** (`hex_id`) - a chart's stable identity in the manifest table: five uppercase hex digits, unique within the workfile, never reused, never renumbered. Names the chart's cache file and is the identity Excel round-trips key on.

**Chart ref** (`chart_ref`) - the display index for a chart, `Chart_0001` style. Renumbers across non-deleted rows whenever the table changes. Never a storage key.

**Row id** (`row_id`) - a Running Order row's position identity. Renumbers on insert, delete or reorder. Never a storage key.

**Software id** - the version identifier for an installed build of ChartGen.

**File version id** - the version identifier for the `.cgw`'s internal structure, stamped into `workfile_info.json` at Save. Independent of the software id: a structure change needs a new file version id regardless of the build.

**Read-Only** - a session opened without claiming the advisory lock. Save is disabled; every other action behaves normally.

**WorkfileState** - the in-memory object holding the complete working state of an open `.cgw`. The only real state in the system, and the only interface other packages use to read or write workfile data during a session.

**`CG_Extracts`** - the fixed folder alongside the `.cgw` where every Excel export lands and every Excel import defaults to.

---

## Template and placeholders

**Placeholder** - a PowerPoint placeholder ChartGen recognises by its native type: Content, Picture, Chart, Clip Art, Table, SmartArt or Media. A native Text placeholder is not in this set; it is populated by text tag replacement only.

**Yellow textbox convention** - placing a yellow-filled textbox in a template to associate it with a data source URL, image path, or Excel range. Resolved against the slide's placeholders into one of three outcomes: fully contained, free-floating, or ambiguous partial overlap.

**Free-floating yellow box** - a yellow box with no overlap with any placeholder on its slide. Its own position and size stand in for a placeholder's.

**Cleaned template** - the template with every yellow annotation textbox stripped out. ChartGen always runs from this, never the marked-up original.

---

## Data shapes and populations

**Chart data** - a comparative dataset for one analysis. Named for where it usually comes from and ends up, but the data itself is agnostic to that and can equally feed a table.

**Data shape** - a container for normalised chart data. The canonical shapes: NumericSeries, NumericCompositional, CategoricalCompositional, TimeSeries, PairedSurveyData.

**Metric-Series** - one measured series within a shape: one name plus one value per unit. A shape can hold several independent Metric-Series, all over the same population. NumericSeries and PairedSurveyData carry them in a flat structure; the compositional shapes and TimeSeries wrap them in a `metrics` list.

**PairedSurveyData** - a canonical shape for data where each unit contributes a collection of individual records rather than one value. Always exactly one Metric-Series. Has no Base Charts, no `chart_type_map.csv` row, and no reference-id converter.

**Population table** - a table sharing the common spine of `unit_id`, `unit_code`, `unit_name`, `soft_parents`, plus any number of `Name()` peer-group columns. A workfile can hold any number of them.

**Master table** - whichever population table sits first in `table_order`. Drives the reporting unit picker and the batch loop. Position is the only definition of master; there is no flag, and moving a table to position 0 makes it master with no further action.

**Soft parent** (`soft_parents`) - a relationship from one population table row to rows in other tables, recorded on the child side only. Not called "parent" because it is not one-to-one: a row may hold zero, one or several ids per table, and may link to any number of tables at once. Resolution is one hop, in both directions.

**Populations string** - the `^`-delimited ordered list of tokens, for example `All^Region()^Selected`, specifying which population layers a chart receives. Every token always produces its own layer, including one resolving to zero units. A token is never dropped for lacking data.

**Population label** (`population_label`) - a field on the data shape identifying which layer a filtered copy represents. Set by `build_population_layers`.

**Summary stats** - the statistics a data shape computes for itself, read per layer via `summary_stats_by_layer`. Distinct from the general benchmarking sense of summary statistics: this is the specific technical term for the data.

**Format modifier** (`format_modifier`) - a shape-level field governing how its own values display.

---

## Running Order and execution

**Running Order** - the user-authored, row-based instruction table defining report assembly: function, parameters, control flags. Strictly an ordered sequence of report content.

**Scope** - the column controlling when a row runs relative to a batch: `normal` once per report, `batch_open` once before the whole batch, `batch_close` once after.

**Enabled** - the per-row on or off switch, stored as `1` or `0`.

**Batch** - producing several outputs in one run.

**Charts sheet round-trip fields** (`CHART_SANDBOX_FIELDS`) - the maintained list of Running Order columns the Charts sheet reads from and writes back to a chart row.

**Page size** - the template's slide width and height, captured once at template processing into workfile settings. The reference dimension for the Sizing widgets' percent unit.

**`CG_Chart_` / `CG_Link_` shape naming** - the names `insert_chart` gives the two PowerPoint shapes it creates: the chart picture as `CG_Chart_{row_id}` and its optional hyperlink icon as `CG_Link_{row_id}`. Goes stale once the Running Order is next reordered, since `row_id` renumbers.

**Position Finder** - a read-only support tool on the Running Order tab, not a Running Order function. Reads a selected shape's live position and size off an already-open PowerPoint, for copying into a row by hand.

**Text Tag** - a placeholder string in template text, for example `[selected-reporting-unit-name]`, replaced with a per-unit value by `update_text`.

**Stat Tag** - a short, permanent `T`-prefixed base-36 id, system-issued or set by hand through the Excel round trip, standing in for one summary-stats value from one chart's own cut of its cached data: one population token, an optional TimeSeries period range or metric-periods conversion, and a reference id. Defined on the Text tab, resolved by `update_text`, and tied to no Running Order row.

A Text Tag needs nothing beyond its own literal string. A Stat Tag needs `hex_id` plus population plus reference id to mean anything, because a reference id is not globally unique.

---

## Runtime objects

**AssemblyContext** - built once per batch run. Carries the open `Presentation`, output and template paths, the run log, the current `ReportContext`, the current Full Unit Set, the default populations string, and any open Excel COM workbooks.

**ReportContext** - the per-report identity object: `unit_id`, `unit_code`, `unit_name`. Rebuilt fresh for each unit. Not passed to Base Chart functions. Carries no organisation identity of its own.

**Full Unit Set** - for the current reporting unit, its own row plus every row one hop out via `soft_parents`, both directions, keyed by table name. Rebuilt once per report. `insert_chart` looks a chart's own `population_table` up here rather than assuming the master table applies to every chart. An entry can hold more than one row, for example an organisation supporting two ICBs, which is expected rather than something to collapse.

---

## Chart construction

**Base Chart** - one of ChartGen's chart-rendering functions. A standalone artefact, one per file, handling one canonical data shape. `CHART_REGISTRY` is the list of built-ins.

**chart_inputs** - the fixed call every Base Chart receives: `population_layers`, `width_emu`, `height_emu`, `tweaks`. Returns image bytes.

**Custom Chart** - a Base Chart saved into a workfile rather than shipped with ChartGen, typically authored with an AI's help. Behaves identically to a built-in from the moment it is saved.

**Chart Store** - a flat, unordered set of independently-authored chart definitions, used as chart components inside Output Table cells. Independent of the Running Order. Each entry carries the same fields as `CHART_SANDBOX_FIELDS`, plus a permanent `C`-prefixed `chart_store_id` and an optional description.

**Reference id** - a short id identifying one statistic in a summary stats table, for example `Mn`, `1Mna`, `P2a`. Scoped per shape type, not globally: the same id means the same statistic in every table of that type. Deliberately short, so it can serve as a literal PowerPoint table replacement tag without changing the cell's size.

**Tweak** (`tweaks`) - the free-text component of `chart_inputs` and `table_inputs`, uninterpreted by anything outside the function it is passed to. Any grammar inside it belongs to the chart or table that reads it.

**TEXT_SCALE / CHART_RENDER_SCALE** - the paired constants implementing the draw-big-then-shrink render mechanism. `CHART_RENDER_SCALE` inflates the canvas at each system-layer call site; `TEXT_SCALE` inflates absolute point-based literals inside each rendering file. All copies must carry the same value.

**Autotable** - a table populated directly from shape statistics rather than by text tag replacement. Not built. Superseded by Output Table for the need it was meant to meet: a table now renders as a single image the same way a chart does, rather than as a native PowerPoint table.

---

## Table construction

**Output Table** - a grid of constant text and Stat Tag values, composited into a single image by a Base Table function. The table equivalent of a chart. Identified by a permanent base-36 `table_id`, system-issued or set by hand through the Excel round trip. Authored on its own tab, not the Charts sheet.

**Base Table** - one of ChartGen's table-rendering functions. A standalone artefact, one per file, the table equivalent of a Base Chart. Not scoped to any data shape. Built in: `plain_grid`, `table_cardtile`, `ci_grid`, `ci_cardtile`.

**table_inputs** - the fixed call every Base Table receives: `content`, `column_widths`, `row_heights`, `width_emu`, `height_emu`, `tweaks`. Returns `(image_bytes, chart_cells)`.

**Custom Table** - a Base Table saved into a workfile rather than shipped with ChartGen. Valid everywhere from the moment it is saved, since a Base Table is not scoped to a data shape.

**Chart-component cell** - a grid cell holding a Chart Store marker, `{Cn}`, naming a chart that belongs in that cell. Not drawn as text: the Base Table function reports the cell's own rectangle back through `chart_cells`, and something else renders the named entry into it, sized to fit the rectangle rather than the entry's stored size. A layered PowerPoint picture in the final report, a spliced SVG `<image>` in the Preview.

---

## Excel integration

**Driver range** - the Excel named range that receives the current `unit_id`.

**Export range** - the Excel named range captured as an image afterwards.
