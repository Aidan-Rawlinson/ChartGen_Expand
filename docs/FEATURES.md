# ChartGen - Features

Current scope and readiness. In pipeline order.

**Complete** confirmed built and working. **Partial** built with a known gap, named. **Not built** no implementation.

---

## Application and session

| Feature | Readiness | Notes |
|---|---|---|
| Sign-in gate | Complete | Full-page form, email pre-filled from last session. Blocks the sidebar, workfile actions and every tab until it succeeds, on every launch route. Token is session-only; username persisted, password never |
| `.bat` launcher | Complete | Creates the venv on first run |
| `.cgw` file format | Complete | |
| `.cgw` file association and custom icon | Complete | Optional. Double-click routes into the normal Open flow, with the same compatibility check and lock decision step |
| Single open workfile at a time | Complete | |
| File version compatibility check | Complete | Hard refuse on an incompatible file version id. No migration attempted |
| Advisory concurrency lock | Partial | Advisory only, and not re-checked after Open |
| Read-Only access | Complete | Offered on every Open regardless of lock state. Enforcement is shallow: Save disabled only |
| Sidebar file operations | Complete | New, Open, Save, Save As, Save and Close, Close Without Saving |
| Project Folder button | Complete | Opens the workfile's own folder in Explorer. Depends on ChartGen running locally, one user per machine |
| Check for Update | Complete | Available only with no workfile open. Reads the release installer's own version, and on confirmation launches it and exits ChartGen so the install can be overwritten in place |
| Outputs folder structure | Complete | `outputs/pptx/` and `outputs/pdf/`, auto-created alongside the workfile on first run |
| SharePoint and OneDrive compatibility | Complete | |

### File operations

| Operation | Behaviour |
|---|---|
| New Workfile | Collects a description and a save location through one native Save dialog, then creates a blank `.cgw`. No project, no population tables |
| Open Workfile | File picker, then a decision step naming the lock state, offering Open or Open Read-Only. Open writes the lock; Read-Only does not |
| Save | Serialises `WorkfileState` to the ZIP and updates `workfile_info.json`. No confirmation. Disabled in a Read-Only session |
| Save As | One native Save dialog for name and location. The OS handles overwrite confirmation. Copies the cleaned template under the new name, releases the old lock, writes a new one. Outputs are not carried across. From a Read-Only session the target folder must differ; on success the session becomes normal |
| Save and Close | Save, clear the lock, return to no-workfile state. Disabled in a Read-Only session |
| Close Without Saving | Confirms if dirty. Clears the lock. In a Read-Only session, closes immediately without confirming |

After a crash the lock fields stay as last written. The next person to open sees the stale lock through the same decision step.

---

## Workfile setup

| Feature | Readiness | Notes |
|---|---|---|
| New Workfile flow | Complete | Collects no project or year. A genuinely blank `.cgw`, with no toolkit involvement at this step |
| Workfile description | Complete | Free text, shown next to the title while the workfile is open. Editable at any time through the sidebar's Workfile Details expander. Plays no part in naming or resolving anything |
| Workfile Details expander | Complete | File name, description, full path, last saved by and at. No project identity, because year and project id are not workfile-level concepts |
| Reporting unit selection | Complete | Selects from the master table only |
| Full Unit(s) display | Complete | The selected unit's own row plus every row one hop out, its own row shown first and bolded |
| Populations tab display and reordering | Complete | Every population table, collapsible, reorderable. Position 0 is the master table |
| Population table Excel round-trip | Partial | Per-table export and import, generic across any table. Identity is `unit_id`: unmatched id added, missing id removed, blank id skipped. No soft-delete flag on these tables. No validation of edited values, so a removed `unit_id` can leave a dangling `soft_parents` reference elsewhere |

---

## Data acquisition

| Feature | Readiness | Notes |
|---|---|---|
| API route: toolkit URL to fetch to store | Complete | The primary data source. One explicit Fetch action, a full refresh of the chart URL table, decoupled from template processing |
| URL to database triage | Complete | Every URL classified `nhs` or `indicators` at manifest-row creation, by path shape alone |
| Chart URL table | Complete | Canonical index of every chart, keyed by `hex_id`. Populated by template extraction and direct entry. Read-only in the UI |
| Direct URL entry | Complete | Export a formatted `.xlsx`, add rows carrying just a URL, import back. Deleting a row removes the chart from the table but keeps its cached data and identity |
| Chart title placeholder replacement | Complete | NHS URLs only. Ten tokens, covering single and double year variants and `\|OPTION_TITLE\|` |
| Manual data entry / in-system analysis | Not built | |

### Population tables

| Feature | Readiness | Notes |
|---|---|---|
| Shared spine | Complete | `unit_id`, `unit_code`, `unit_name`, `soft_parents`, plus any number of `Name()` peer-group columns |
| Automatic creation, NHS | Complete | Triggered per chart, inside the fetch, the first time a chart's own project and year is seen. Not a user action |
| Automatic creation and merge, Indicators | Complete | Merges on every fetch rather than building once, because one response spans a project's full period history and submissions drop in and out over time |
| `nhs_organisations` merge across projects | Complete | A further project's organisations are appended by `unit_id`, never overwritten. Assumes each peer-group column is a value handed over per organisation by the API |
| `soft_parents` recording | Complete | Child side only. Resolution is one hop, both directions |
| `Region()` peer group | Complete | Resolved per organisation from the API at build time |
| Additional `Name()` peer-group columns | Complete | Both empty-bracket, meaning the selected unit's own group, and explicit-value forms work end to end: column discovery, Running Order multi-select auto-populated with every distinct value, and resolution against the population scope. Blank and `x` are excluded from discovery and treated as no group |
| Multi-level hierarchy | Not built | One hop between any number of tables is built. A deep chain, walking from one table through a related table's own further relationships, is not |

---

## Template

| Feature | Readiness | Notes |
|---|---|---|
| Upload and processing pipeline | Complete | |
| Named placeholder element slots | Complete | |
| Yellow textbox convention | Complete | Classified by content: toolkit URL, image path, Excel path with driver and export ranges, or the literal word "Table". Detected by colour whether the fill is literal or theme-referenced. Resolved into three outcomes: fully contained with 1mm tolerance, no overlap, or ambiguous partial overlap. Unrecognised content is warned, not silently stripped |
| Cleaned template production | Complete | |
| Cleaned template as user-owned asset | Complete | Two edit tiers. Cosmetic edits picked up silently on the next run. Structural edits need a re-upload, which regenerates the Running Order |
| Validation on run | Complete | Compares slide layout names between the reference copy and the live template. Warns on mismatch, does not block |
| Page size capture | Complete | Slide width and height captured once into workfile settings |
| User template creation, self-service placeholder positioning | Not built | |

---

## Report definition

| Feature | Readiness | Notes |
|---|---|---|
| Running Order CSV storage as the master processing document | Complete | |
| Running Order `.xlsx` round-trip | Complete | With formatting and validation |
| Auto-generation from template | Complete | |
| Running Order tab | Complete | Master and detail, with a shape-filtered chart type dropdown |
| Position Finder | Complete | Collapsible section under the Running Order tab. Reads the selected shape's live position and size off an already-open PowerPoint. Resolves a hyperlink icon's position as an offset from its matching chart by name, where the match is on the same slide. Writes nothing back |
| Per-row on/off flag | Complete | |
| Charts sheet round-trip | Complete | Loads a Running Order chart row, a cached dataset directly, or a Chart Store entry. Writes back via Overwrite, Insert above or Insert below |
| Charts sheet sandbox persistence | Complete | Control values captured on Save, Save As and Save and Close, restored once per Open, independent of whether they were ever committed to a row. Zoom and an in-progress Custom Charts paste-back are excluded |
| Charts sheet summary stats display | Complete | One table per population layer and metric-series, with a reference id alongside each statistic |
| Charts sheet unit list display | Complete | One table per population layer: unit id, code, name. A layer with no units shows an explicit note rather than being omitted |
| Charts sheet Export Picture | Complete | Re-renders the current chart, respecting an unsaved Custom Charts preview override, and writes the SVG to `CG_Extracts`. The file is deliberately the oversized render, matching what a PPTX embeds |
| Conditional Running Order logic | Not built | Needed for algorithmic reports |
| `insert_slide` / `insert_section` / `delete_slide` | Not built | |
| `table_data_lift`, `submission_list` | Not built | |

### Running Order functions

| Function | Readiness | Notes |
|---|---|---|
| `create_ppt` | Complete | Also forces image compression off on the presentation |
| `set_default_populations` | Complete | |
| `insert_chart` | Complete | Renders a Base Chart from cached data. Resolves the name built-in first, then the workfile's Custom Charts. Selected-unit highlighting comes from the `"Selected"` population layer. Names the picture for traceback. Optional hyperlink icon linked to the shape's recorded source URL |
| `insert_table` | Complete | Renders a Base Table from an Output Table's grid, the same way `insert_chart` renders a chart. Resolves built-in first, then Custom Tables |
| `insert_picture` | Complete | `[code]` and `[id]` token substitution, aspect ratio preserved |
| `insert_from_excel` | Complete | With `open_excel` and `close_excel`. Requires COM |
| `update_text` | Complete | Ordinary text frames and PowerPoint table cells alike, both tag families. Report level tags come from `REPORT_TEXT_TAGS`, the one list the Text tab's table also renders |
| `empty_placeholder` | Complete | |
| `save_ppt` | Complete | |
| `save_pdf` | Complete | Disabled by default in generated Running Orders |

---

## Chart construction

| Feature | Readiness | Notes |
|---|---|---|
| Base Chart library | Complete | Each a standalone artefact with no shared helpers. No chart renders a title. Takes EMU directly. Renders as SVG with Calibri and real `<text>` |
| Custom Charts | Complete | Download bundle, AI edit, paste-back validation, live preview, save. Validation is static only: imports and signature, not what the function returns. No runtime sandboxing. A saved one behaves identically to a built-in everywhere |
| Period range trim, TimeSeries | Complete | `start_period` and `end_period` trim the shape before population filtering. Authored through the Charts sheet's Period Range box |
| Convert periods to metrics | Complete | `metric_periods` converts a TimeSeries row into a NumericSeries snapshot before rendering, one metric per source Metric-Series per period. Feeds any NumericSeries chart type |
| Populations string as a Running Order control | Complete | |
| Peer group as a data filter | Complete | A peer token leading the populations string narrows the data scope |
| Peer group as a visualisation layer | Complete | A peer token following `All` keeps the full population and renders the group as an additional layer. Per-chart rendering of layers is prototype level |
| Reporting unit highlighting, NumericSeries | Complete | Selected can resolve to more than one unit where the chart's own population table has a one-to-many relationship to the reporting unit |
| Reporting unit highlighting, TimeSeries | Complete | Selected units drawn as their own lines. Same one-to-many handling |
| Reporting unit highlighting, NumericCompositional | Not built | Per-unit values are not in the data shape as returned by the API |
| Reporting unit highlighting, CategoricalCompositional | Not applicable | These charts show population aggregates only. No per-unit value exists |
| PairedSurveyData | Partial | The shape is built and wired into dispatch and cache reading, so it can be constructed, filtered and have its stats read. No transformer populates one from real API data, no Base Chart accepts it, and it has no Stat Tags integration |
| Tweaks: reference lines | Partial | Two charts only, `column_ci_full` and `line_ci_full`, each through its own `target` convention: a fixed value, or `median` to track the metric's own median, drawn as a dashed line with a label. Not a general mechanism |
| Tweaks: axis control, min, max, unit, format | Not built | Needed to produce interpretable charts |
| Tweaks: conditional and group colouring | Not built | |
| Tweaks: chart type conversion | Not built | |
| Multiple units from the same organisation in a distinct colour | Not built | |

---

## Output Tables

| Feature | Readiness | Notes |
|---|---|---|
| Grid create, edit, resize | Complete | An (N+1) by (M+1) grid: widths and heights as percentages each summing to about 100%, plus content cells. Validated on an explicit Update, tolerance plus or minus 0.5%, never auto-corrected. A typed `<br>` becomes a real line break at resolution |
| Creation via a `Table` yellow box | Complete | Every occurrence always creates a brand-new table, auto-named, at a fixed 7 by 4 starting size. Never matched against an existing table by name, even on re-upload, so re-uploading the same template twice produces two independent sets |
| Base Table library | Complete | `plain_grid`, `table_cardtile`, and their two-row-header CI-report variants `ci_grid` and `ci_cardtile`. Each a standalone artefact with no shared helpers, returning image bytes plus any chart-cell rectangles. Renders as SVG with Calibri and real `<text>` |
| Custom Tables | Complete | Mirrors Custom Charts. No shape-type scoping, so a saved one is valid everywhere immediately. An optional toggle also bundles full detail for every embedded chart cell's Chart Store entry, so the table can be rebuilt in full from one document |
| Excel round-trip | Complete | Full-replace, mirroring the grid's own spreadsheet shape. Content cells offer a Stat Tag dropdown through a hidden list sheet, with free text still accepted. A percentage-formatted cell is read back through its number format, not its raw value |
| Shared selection box | Complete | One selection shared by Edit Grid and Preview. "+ New Output Table" sits last, revealing inline creation controls |
| Preview sandbox | Complete | Table type, tweaks, sizing, Save to Running Order, Custom Tables, Reset. State persists across Save and reopen |
| Tag resolution in cells | Complete | Report level tags and Stat Tags alike, through `update_text`'s own two token builders, not a duplicated path |
| Chart-component cells | Complete | The Base Table function recognises the marker, skips drawing it as text, and reports the cell's rectangle. Rendered as a layered PowerPoint picture in the report, or a spliced SVG image in the Preview. Never merged into the table's own image. A blank `populations` correctly inherits the workfile default in both paths |
| Running Order placement for a manually created table | Complete | Appends an `insert_table` row immediately above `save_ppt`, with no slide or position and default sizing. The user sets position afterwards. A yellow-box table gets its row at template processing with real position |
| Chart Store | Complete | A third Charts sheet entry point alongside Running Order row and Data shape. Save-back offers Add and Overwrite only, no position concept. A toggle swaps the chart preview for a table of every entry, with delete, export and import |
| Autotables | Not built, superseded | Superseded by Output Tables. A table now renders as a single image from a resolved grid rather than as a native PowerPoint table populated from chart statistics |
| Multi-unit table expansion | Not built | |

---

## Text and variable content

| Feature | Readiness | Notes |
|---|---|---|
| Per-unit text tags | Complete | Presentation-wide, single pass, handles tokens split across runs, and covers table cells. One tag currently defined; the mechanism is general |
| Summary Stat Tags | Complete | Each stands in for one summary-stats value from one chart's own cut of its cached data: a single population token, an optional period range or metric-periods conversion, and a reference id. Defined and previewed on the Text tab, resolved at generation time in ordinary text and table cells alike. Tied to no Running Order row. Full-replace Excel round-trip |
| Pre-scan of the template for tag positions | Not built | Tags are located per report by walking the presentation at generation time. No upfront scan, no stored map |
| Conditional text, formula-driven tag values | Not built | |

---

## Execution and output

| Feature | Readiness | Notes |
|---|---|---|
| Batch processing loop | Complete | |
| Run Selected | Complete | Single unit, QA mode. Does not advance the batch cursor |
| Run Batch | Complete | Next N, queue-aware |
| Run All | Complete | Full population |
| Batch cursor | Complete | Persisted in settings, advances on success only |
| Live run log table | Complete | Surfaces the first error per unit, prefixed with its row id |
| Error handling and batch resumption | Not built | |
| Individualised batch reports, PowerPoint and PDF | Complete | The core use case |
| Standalone reports | Complete | A batch of one, falling out of the batch pipeline naturally |
| Bespoke and algorithmic reports | Not built | Requires conditional Running Order logic |
| Word output | Not built | No requirement identified |

---

## Known limitations

Each of these has a real consequence for someone using ChartGen.

**PDF raster resolution.** A raster picture in an exported PDF can render below its true source resolution, inherent to PowerPoint's own PDF engine. This no longer affects ChartGen's own generated images, which are all SVG, but it still affects `insert_picture`, which places user-supplied rasters unchanged.

**Searchable text.** Table and chart text was not searchable or selectable under the original outline-path rendering approach. Whether that still holds now text is rendered as real `<text>` has not been re-verified.

**Thin strokes in some PDF viewers.** Unhinted vector text can render capital I, lowercase l and the pipe character fractionally too heavy at low zoom, confirmed in Adobe Reader. Cosmetic and zoom-dependent.

**Theme gradient fills.** Shaded and gradient theme fill variants are not modelled in yellow-box detection; the base scheme colour is used unmodified. Fine for detecting yellow, not a general theme-colour renderer.

**Free-floating box precision.** A free-floating yellow box is only as precise as the designer drew it. Pixel-perfect placement means editing the EMU columns or the Sizing fields by hand.

**Reference id stability.** A reference id's meaning depends on the shape's current series and component count. A tag referencing `Mn` on a single-series chart means something different, or breaks, if a second metric-series is later added to that chart.

**Shape name staleness.** `CG_Chart_` and `CG_Link_` names go stale as soon as the Running Order is next reordered or edited, because `row_id` renumbers. Accurate at generation time, not a durable identity.

**Duplicate Output Tables on re-upload.** A `Table` yellow box carries no identity, so re-uploading a template produces a fresh set of tables rather than reusing the existing set. Running Order rows have to be re-linked by hand.

**Shallow read-only enforcement.** Save is disabled; everything else behaves normally, so unsaved edits are lost unless rescued through Save As.

**Stale locks.** A lock may survive a crash or force-quit with no way to distinguish it from a live one.

**Custom code and contract changes.** A Custom Chart or Custom Table saved against an older rendering contract must be re-saved by hand. Nothing migrates it.

**Deep hierarchies.** `soft_parents` resolves one hop only. A chain such as Country to Region to ICB to Organisation is not walked automatically.
