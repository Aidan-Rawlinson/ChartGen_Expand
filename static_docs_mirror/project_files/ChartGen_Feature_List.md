# ChartGen — Feature List

*TBN Internal · Describes current scope and readiness only*

**Readiness** — Complete (confirmed built and working) · Partial (implemented but with a known gap, noted below) · Not built (no implementation yet)

Structured in pipeline order: application/session foundations, then workfile setup, data acquisition, template and report definition, content construction, execution, and output.

---

# Part 1 — Application & Session Foundations

## Credentials & authentication

| Feature | Readiness | Notes |
|---|---|---|
| Sign-in gate | Complete | Full-page sign-in form — email (pre-filled from last session), password, Sign in button — blocks the sidebar, workfile creation/opening, and every tab until it succeeds, whether launched directly or via a `.cgw` file association. Sign Out (sidebar) ends the session. Session-only token; username persisted to `credentials.csv`, password never saved. |

---

## Workfile / file structure

| Feature | Readiness | Notes |
|---|---|---|
| `.bat` launcher | Complete | |
| Workfile file format (`.cgw`) | Complete | See Architecture document. |
| Concurrency via `workfile_info.json` lock fields | Partial | See Architecture Decisions 4–6. The lock itself remains advisory and is not re-checked after Open. |
| File version compatibility check | Complete | See Functional Spec Section 5.1. Hard refuse on an incompatible file version id; no migration attempted. |
| Read-Only workfile access | Complete | See Architecture Decision 6. Offered on every Open regardless of lock state; enforcement is shallow (Save disabled only). |
| Sidebar file operations (New, Open, Save, Save As, Save and Close, Close Without Saving) | Complete | See Architecture Decision 6. |
| Outputs folder structure (`outputs/pptx/`, `outputs/pdf/`) | Complete | Auto-created alongside the workfile on first run. |
| SharePoint/OneDrive compatibility | Complete | See Architecture Decision 8. |

---

## Application model

| Feature | Readiness | Notes |
|---|---|---|
| Single open workfile (`.cgw`) at a time | Complete | |
| `.cgw` file type | Complete | ChartGen creates, reads, and writes `.cgw` files correctly. |
| File association (double-click a `.cgw` file to open ChartGen) | Complete | Optional, not required — ChartGen opens with no workfile the same as launching normally. Reuses the same file version compatibility check and concurrency decision step as Open Workfile. |
| Custom icon for `.cgw` files | Complete | |

---

# Part 2 — Workfile Setup

## Workfile setup

| Feature | Readiness | Notes |
|---|---|---|
| New Workfile flow (description → single native Save dialog) | Complete | See Functional Spec Section 4. Collects no project/year — creates a genuinely blank `.cgw`; no toolkit involvement at this step at all. |
| Workfile description field | Complete | Free text, "what is this workfile for"; shown next to the ChartGen title in the app header for as long as the workfile is open. For the person, not the system — plays no part in naming the file or resolving anything. Editable at any time via the Workfile Details expander in the sidebar, not just at creation. |
| Native Save dialog (New Workfile and Save As) | Complete | One OS dialog for filename and location together; the OS itself handles overwrite confirmation, so neither flow has its own overwrite step. |
| Workfile Details (sidebar expander) | Complete | Collapsed by default — file name, description, full file path, last-saved-by/at. No project identity shown — year/project_id/project_name are not workfile-level concepts (see Population tables, Part 3). |
| Population tables — Excel download/upload round-trip | Partial | Per-table download/upload on the Populations tab, generic across any table. Identity is `unit_id`: unmatched id added, missing id removed (no soft-delete flag on these tables), blank id skipped. No validation of edited values — a removed `unit_id` can leave a dangling `soft_parents` reference elsewhere. See Functional Spec Section 7.2. |

---

## Select

| Feature | Readiness | Notes |
|---|---|---|
| Reporting unit selection tab — reporting unit selectbox (name / code / ID) | Complete | Selects from the master table only (whichever population table sits on top — see Populations, Part 3). |
| Reporting unit selection tab — Full Unit(s) | Complete | For the selected unit, shows its own row plus every row related to it one hop out (via `soft_parents`, both directions) — reporting unit's own row shown first and bolded. |
| Populations tab — table display, reordering | Complete | Every population table, collapsible, reorderable via ▲/▼. Whichever table sits in position 0 is the master table — no separate flag, position is the only source of truth. Drives the reporting unit picker and the batch loop. |

---

# Part 3 — Data Acquisition

## Data acquisition

| Feature | Readiness | Notes |
|---|---|---|
| API route (toolkit URL → data fetch → store) | Complete | Primary data source. Single explicit fetch — a full refresh of the chart URL table — decoupled from template processing. |
| URL-to-database triage | Complete | Every URL is classified `nhs` or `indicators` at manifest-row creation, by path shape alone. See Architecture Decision 10. |
| Chart URL table (`manifest.csv`) | Complete | Canonical index of every chart in the workfile, keyed by stable hex id. Populated by template extraction and direct entry; read-only in the UI. See Architecture Section 5 for the schema. |
| Direct URL entry (Excel round-trip) | Complete | Download formatted `.xlsx`, add rows with just a URL, upload. Row deletion removes the chart from the table; cached data and identity are retained. |
| Manual data entry / in-system analysis | Not built | Supplementary route; not currently used. |
| Chart title placeholder replacement (NHS URLs only) | Complete | Placeholders replaced: `|DOUBLE_YEAR_CURRENT|`, `|DOUBLE_YEAR_PREVIOUS|`, `|DOUBLE_YEAR_MINUS_2|`, `|DOUBLE_YEAR_NEXT|`, `|SINGLE_YEAR_CURRENT|`, `|SINGLE_YEAR_PREVIOUS|`, `|SINGLE_YEAR_MINUS_2|`, `|SINGLE_YEAR_MINUS_3|`, `|SINGLE_YEAR_NEXT|`, `|OPTION_TITLE|`. |

---

## Reference / supporting data

| Feature | Readiness | Notes |
|---|---|---|
| Population tables — `nhs_organisations` + `submissions_{year}_{project_id}` (shared spine) | Complete | Every population table shares the same columns — `unit_id`, `unit_code`, `unit_name`, `soft_parents`, plus any number of `Name()` peer-group columns. See Architecture Section 5. |
| Automatic population-table creation | Complete | Triggered per chart, inside the toolkit fetch, the first time a chart's own project/year is seen on this workfile — not a user-facing action. See Functional Spec Section 7. |
| `nhs_organisations` merge across projects | Complete | A further project's organisations are appended by `unit_id`, not overwritten; existing rows untouched. Assumes each peer-group column (e.g. `Region()`) is a value handed to us per-organisation by the API, not something computed from the full table — would need revisiting if that stopped being true. |
| `soft_parents` relationship recording | Complete | Recorded on the child side only; see Glossary. Resolution is one hop only, in both directions (a row's own links, and other rows linking to it) — a chain of more than two tables (e.g. Country→Region→ICB→Organisation) is not walked automatically. |
| Peer group assignments — `Region()` | Complete | Resolved per organisation from the API at population-table build time, written into whichever population table it belongs to. |
| Additional peer group columns (`Name()`) | Complete | Both empty-bracket (`Region()`, the selected unit's own group) and explicit-value (`Region(Wales)`, a named group) tokens are supported end-to-end: column discovery, Running Order multi-select (auto-populated with every distinct value per column), and resolution against the population scope. Blank and `x` values are excluded from discovery and treated as no group. |
| Multi-level hierarchy model | Not built | `soft_parents` covers one-hop relationships between any number of tables (built, see above); a genuinely deep chain — walking from one table to a related table's own further relationships — is not built. |
| Population table — `submissions_timeseries_{project_id}` (Indicators) | Complete | Own naming convention (no year component), own shared spine including `Region()` sourced from `nhs_organisations` at merge time. See Architecture Decision 10. |
| Automatic population-table creation/merge (Indicators) | Complete | Merges on every fetch, not build-once — contrast the NHS row above. A single fetch response already spans a project's full period history, and submissions genuinely drop in and out over time. See Architecture Decision 10. |

---

# Part 4 — Template & Report Definition

## PowerPoint template

| Feature | Readiness | Notes |
|---|---|---|
| Template upload and processing pipeline | Complete | |
| Named placeholder element slots | Complete | |
| Yellow textbox convention (URL / picture / Excel / table) | Complete | Yellow boxes are classified by content: toolkit URL (chart), image path (picture), Excel path with driver/export ranges, or the literal word "Table" (Output Table). Detected by colour whether the fill is literal or theme-referenced (Architecture Decision 14). Resolved against the slide's placeholders into three outcomes: fully contained, with 1mm tolerance (placeholder's own position/size used), no overlap (free-floating — the box's own position/size used instead), partial overlap (ambiguous — left unclassified and unremoved, warned). Unrecognised content is also warned, not just silently stripped. See Architecture Decisions 13–14. |
| Cleaned template production | Complete | |
| Cleaned template as user-owned asset | Complete | Two edit tiers: cosmetic edits picked up silently on next run; structural edits require re-upload, which regenerates the Running Order. See Architecture Decision 2. |
| Template validation on run (slide layout comparison) | Complete | Compares slide layout names between the `.cgw` reference copy and the live template; warns on mismatch, doesn't block. See Architecture Decision 3. |
| Page size capture at template processing | Complete | Slide width/height captured once into workfile settings; the reference for the Charts sheet's percent-of-shorter-dimension sizing unit. See Architecture Decision 11. |
| User template creation (self-service placeholder positioning) | Not built | |

---

## Report assembly

| Feature | Readiness | Notes |
|---|---|---|
| Running Order (.csv storage) as master processing document | Complete | |
| Running Order .xlsx for user entry with formatting and validation (export/import) | Complete | |
| Running Order auto-generation from template | Complete | |
| Running Order Streamlit tab (master/detail UI) | Complete | Shape-filtered chart type dropdown. |
| Control flag (row on/off) | Complete | |
| `create_ppt` | Complete | |
| `insert_chart` | Complete | Renders a Base Chart from cached data. Resolves `base_chart_name` against the built-in library first, then a workfile's own saved Custom Charts. Selected-unit highlighting comes from the `"Selected"`-labelled `population_layers` entry — no `report_context` is passed to a chart. See Chart construction, Part 5. |
| `insert_table` | Complete | Renders a Base Table from an Output Table's grid, the same way `insert_chart` renders a chart. Resolves `table_type_ref` against the built-in library first, then a workfile's own saved Custom Tables. See Output Tables, Part 5. |
| `empty_placeholder` | Complete | |
| `save_ppt` | Complete | |
| `save_pdf` | Complete | Disabled by default in generated Running Orders. |
| `set_default_populations` | Complete | The Charts sheet no longer reads this row directly to default its own preview — see Charts sheet round-trip, below. |
| `update_text` | Complete | Covers ordinary text frames and PowerPoint table cells alike, both tag families (per-unit tags and Stat Tags). See Text / variable content, Part 5, and Architecture Decision 20. |
| `insert_picture` | Complete | `[code]`/`[id]` token substitution; aspect ratio preserved. |
| Insert Content From Excel | Complete | Requires `pywin32`. Implemented via three functions: `open_excel`, `insert_from_excel`, `close_excel`. |
| `table_data_lift` | Not built | |
| Conditional Running Order logic (insert/delete slides per unit) | Not built | Needed for algorithmic reports. |
| `insert_slide` / `insert_section` / `delete_slide` | Not built | |
| `submission_list` | Not built | |
| Charts sheet ↔ Running Order round-trip | Complete | Loads a Running Order chart row, a cached dataset directly, or a Chart Store entry; writes `base_chart_name`, `cache_file`, `populations`, `start_period`, `end_period`, `metric_periods`, `width_emu`, `height_emu`, `tweaks` back via Overwrite, Insert above, or Insert below. See Functional Spec Section 9.3, Architecture Decision 11. |
| Chart Store (flat, unordered chart-def storage) | Complete | A third Charts sheet entry point ("Chart Store line") alongside Running Order row and Data shape; save-back offers Add/Overwrite only, no position concept. "Show Chart Store"/"Hide Chart Store" toggle swaps the chart preview for a table of every entry (delete/download/upload, full-replace Excel round-trip mirroring Stat Tags). Ids are `C`-prefixed (`C1`, `C2`, ...), distinguishing them from a Stat Tag's `T`-prefix, since both can now appear together inside an Output Table cell. Now consumed as chart components inside Output Table cells — see Chart-component cells, below. See Functional Spec Section 10.10, Architecture Decisions 28 and 30. |
| Charts sheet sandbox state persistence (Save/reopen) | Complete | The sandbox's own current control values (bound row, cache file, chart type, populations, period range/metric-periods, tweaks, sizing, save-action/target) are captured into `settings["charts_sheet_state"]` on Save/Save As/Save and Close and restored once per Open — independent of whether they've been committed to a Running Order row via "Save to Running Order". Zoom (already screen-only) and an in-progress Custom Charts paste-back are excluded. See Architecture Decision 21. |
| Charts sheet summary stats display | Complete | One table per (population layer × metric-series), with a short per-shape-type reference id (e.g. `Mn`, `1Mna`, `P2a`) alongside each statistic, read directly off the same population layers passed to the chart. See Functional Spec Section 9.4, Architecture Decisions 15 and 17. |
| Charts sheet unit list display | Complete | One table per population layer — unit id, code, name — read directly off the same population layers passed to the chart. See Functional Spec Section 9.4, Architecture Decisions 15 and 17. |

---

# Part 5 — Content Construction

## Chart construction

| Feature | Readiness | Notes |
|---|---|---|
| Base Chart library (20 charts across 4 data shapes) | Complete | No chart type renders a title. Each is a standalone artefact with no shared internal helpers — see Custom Charts, below. Takes `width_emu`/`height_emu` directly (Architecture Decision 29). Renders as SVG with Calibri (Architecture Decision 27) -- not searchable/selectable in PowerPoint or PDF. |
| Custom Charts (download bundle, AI edit, paste-back validation, live preview, save) | Complete | User- or AI-authored Base Charts saved into a workfile via a self-contained download/paste-back flow. Validation is static only — checks imports and function signature, not what the function returns — no runtime sandboxing. A saved Custom Chart behaves identically to a built-in everywhere a chart type is listed or resolved. See Functional Spec Section 10.9, Architecture Decision 18. |
| TimeSeries chart rendering | Complete | Three chart types: `period_line_chart`, `median_comparison_linechart`, `full_lines_linechart`. Renders the first Metric-Series only. |
| Period selection / cutting (TimeSeries) | Complete | Running Order `start_period`/`end_period` columns (period_id, blank = full range) trim the shape before population-layer filtering. Authored via the Charts sheet's Period Range box. See Functional Spec Section 10.7. |
| Convert periods to metrics (TimeSeries → NumericSeries snapshot) | Complete | Running Order `metric_periods` column (one or more period_ids) converts a TimeSeries row into a NumericSeries snapshot before rendering — one metric per source Metric-Series × period. Feeds any NumericSeries chart type. See Functional Spec Section 10.8. |
| Populations string — Running Order control | Complete | |
| Reporting unit highlighting — NumericSeries (6 charts) | Complete | Selected can resolve to more than one unit, when the chart's own population table (`population_table` on the data shape) has a one-to-many relationship to the reporting unit — e.g. an organisation with several submissions. See Functional Spec Section 10.4. |
| Peer group as data filter (peer token leading the populations string) | Complete | Chart data scope narrows to the peer group; e.g. `Region(Wales)^Selected` shows Welsh units only. |
| Reporting unit highlighting — NumericCompositional | Not built | Per-unit values not currently in the data shape as returned from the API. |
| Reporting unit highlighting — CategoricalCompositional | Not applicable | These charts show population aggregates only; no per-unit value exists. |
| Reporting unit highlighting — TimeSeries | Complete | Selected unit(s) drawn as their own line(s); same one-to-many handling as other shapes. |
| Selection identity in summary stats (all 20 charts) | Complete | |
| Peer group as visualisation layer (peer token following `All`) | Complete | Full population retained; the peer group is rendered as an additional layer. Per-chart rendering of layers is prototype-level. |
| Autotable populations (separate from chart populations) | Not built | No `table_populations` field exists on `insert_chart` rows. |
| Multiple units from same org (distinct colour) | Not built | |
| Tweaks — reference lines (`add_line`, `Add_Line_Label`) | Not built | |
| Tweaks — axis control (min/max, unit, format) | Not built | Needed to produce interpretable charts. |
| Tweak hook architecture (3 intervention points) | Not built | Design settled, but not yet implemented in code. |
| Tweaks — conditional / group colouring | Not built | |
| Tweaks — Bespoke_Labels, add_selected_codes | Not built | |
| Tweaks — chart type conversion (`YN_2_PIE`) | Not built | |

---

## Output Tables

| Feature | Readiness | Notes |
|---|---|---|
| Output Table grid (create, edit, resize) | Complete | Authored as an (N+1) × (M+1) grid — column widths/row heights (% of the table's own width/height, each expected to sum to ~100%) plus content cells (constant text or a Stat Tag id). Validated on an explicit Update, tolerance ±0.5%, never auto-corrected. A typed `<br>` (also `<br/>`/`<br />`) is converted to a real line break at content resolution time. See Architecture Decisions 23, 33. |
| Output Table creation via yellow box (`Table`) | Complete | Every occurrence, matched or free-floating, always creates a brand-new Output Table — auto-named (`Table_1`, `Table_2`, ...), fixed starting size (7 rows × 4 columns) — never matched against an existing one by name, even on re-upload. See Architecture Decision 23. |
| Output Table Excel download/upload round-trip | Complete | Full-replace, mirroring the grid's own spreadsheet shape directly (not a flat table) — content cells offer a Stat Tag id dropdown via a hidden list sheet, free text still accepted alongside it. A percentage-formatted cell (e.g. typed as `5%`) is read back via its own number format, not its raw underlying value. See Architecture Decision 34. |
| Base Table library (2 styles) | Complete | `plain_grid`, `table_cardtile` — trimmed back from ten (Architecture Decision 30). Each a standalone artefact, no shared internal helpers, taking `table_inputs` (resolved grid, sizing, tweaks) and returning `(image_bytes, chart_cells)` — the second value reports any chart-component cell's own rectangle, in EMU (see below). See Architecture Decisions 24, 29, 30. Renders as SVG with Calibri (Architecture Decision 27) -- not searchable/selectable in PowerPoint or PDF. |
| Custom Tables (download bundle, AI edit, paste-back validation, live preview, save) | Complete | User- or AI-authored Base Tables saved into a workfile via a self-contained download/paste-back flow, mirroring Custom Charts. No shape-type scoping — a saved Custom Table is valid everywhere immediately. An optional toggle also bundles full detail (settings, source, live data) for every embedded chart-component cell's own Chart Store entry, so the table can be rebuilt in full from one document. See Architecture Decisions 24, 35. |
| Output Tables tab — shared selection box (Running Order row / Output Table by name) | Complete | One selection, shared by Edit Grid and Preview modes; "+ New Output Table" last in the list, revealing inline creation controls. See Functional Spec Section 9.6. |
| Output Tables tab — Preview sandbox (table type, tweaks, sizing, Save to Running Order, Custom Tables, Reset) | Complete | Mirrors the Charts sheet's own mechanics wherever the concepts match. Sandbox state persists across Save/reopen (`settings["output_tables_sheet_state"]`), the same pattern as the Charts sheet (Architecture Decision 21). |
| Stat Tag resolution in Output Table cells | Complete | Reuses `update_text`'s own token-building logic (`build_stat_tag_tokens`), not a duplicated resolution path. |
| Chart-component cells (`{Cn}`, a Chart Store entry embedded in a table cell) | Complete | A Base Table's own function recognises the marker, skips drawing it as text, and reports back the cell's own rectangle in EMU. Rendered as a layered PowerPoint picture in the final report (`insert_table.py`) or a spliced-in SVG `<image>` in the Output Tables Preview — never merged into the table's own image either way. An entry's own blank `populations` field correctly inherits the workfile's current default in both rendering paths. See Architecture Decisions 30, 31. |
| Running Order placement for a manually-created Output Table | Complete | Creating a table on the Output Tables tab appends an `insert_table` row automatically, immediately above `save_ppt` — no real slide/position yet, sized 70%/50% width/height by default; the user sets slide/position afterwards via the tab's own Preview sandbox or the Running Order tab. A yellow-box-created table continues to get its row automatically at template processing, with real position from the template. |

---

## Tables

| Feature | Readiness | Notes |
|---|---|---|
| Text-tag-based table population (basic tables) | Complete | Achieved via Stat Tags placed in a table cell plus `update_text`'s table-cell coverage — no dedicated table-population mechanism of its own. |
| Autotables (statistics from chart construction, auto-populating a native PowerPoint table) | Not built, superseded | Superseded by Output Tables (above) for the need it was intended to meet — a table now renders the same way a chart does, as a single image from a resolved grid, rather than a native PowerPoint table populated from chart statistics. Summary stats remain computed by the shape modules and read directly, on demand, by any consumer that needs them, unchanged. |
| Multi-unit table expansion | Not built | |

---

## Text / variable content

| Feature | Readiness | Notes |
|---|---|---|
| Text tag replacement — per-unit tags (e.g. `[selected-reporting-unit-name]`) | Complete | Presentation-wide, single-pass, handles tokens split across runs, and PowerPoint table cells. One tag currently defined; the mechanism is general. See Functional Spec Section 12. |
| Summary Stat Tags | Complete | Short, permanent, `T`-prefixed base-36 tag ids (e.g. `[T3]`) each standing in for one summary-stats value from one chart's own independently-authored cut of its cached data — a single population token, optional TimeSeries period range/metric-periods conversion, and a Reference id. Defined and previewed on the Text tab; resolved by `update_text` at generation time, in ordinary text and table cells alike. Not tied to any Running Order row. Excel download/upload round-trip (full replace on upload, matching the Running Order xlsx's own pattern rather than the manifest table's identity-merge one). See Functional Spec Section 12.1, Architecture Decisions 19 and 30. |
| Pre-scan template for tag positions | Not built | Text tags are located per report by walking the presentation at generation time; no upfront scan or stored map exists. |
| Conditional text (formula-driven tag values) | Not built | |

---

# Part 6 — Execution

## Batch processing

| Feature | Readiness | Notes |
|---|---|---|
| Batch processing loop | Complete | |
| Run Selected (single unit, QA mode) | Complete | Does not advance the batch cursor. |
| Run Batch (next N, queue-aware) | Complete | |
| Run All (full population) | Complete | |
| Batch cursor (persisted queue position) | Complete | Persisted in `settings.csv`; advances on success only. |
| Live run log table | Complete | |
| Error handling and batch resumption | Not built | |

---

# Part 7 — Output

## Output types

| Feature | Readiness | Notes |
|---|---|---|
| Individualised batch reports (PowerPoint / PDF) | Complete | The core use case — everything else is contingent on this working. |
| Standalone reports | Complete | A batch of one; falls out of the batch pipeline naturally. |
| Bespoke / algorithmic reports (conditional structure) | Not built | Requires conditional Running Order logic; adds significant complexity. |
| Word output | Not built | No current requirement identified. |
