# ChartGen — Feature List

*TBN Internal · Describes current scope and readiness only*

**Readiness** — Complete (confirmed built and working) · Partial (implemented but with a known gap, noted below) · Not built (no implementation yet)

Structured in pipeline order: application/session foundations, then workfile setup, data acquisition, template and report definition, content construction, execution, and output.

---

# Part 1 — Application & Session Foundations

## Credentials & authentication

| Feature | Readiness | Notes |
|---|---|---|
| Credential validation (Config tab) | Complete | Single box — email, password, Validate button — session-only token; username persisted, password never saved. Not a launch gate; a workfile can be created, opened, and saved with none validated. |

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
| Workfile description field | Complete | Free text, "what is this workfile for"; shown next to the ChartGen title in the app header for as long as the workfile is open. For the person, not the system — plays no part in naming the file or resolving anything. |
| Native Save dialog (New Workfile and Save As) | Complete | One OS dialog for filename and location together; the OS itself handles overwrite confirmation, so neither flow has its own overwrite step. |
| Details tab (file identity, save history) | Complete | Read-only file path and last-saved-by/at. No project identity shown — year/project_id/project_name are not workfile-level concepts (see Population tables, Part 3). |

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
| Yellow textbox convention (URL / picture / Excel) | Complete | Yellow boxes are classified by content: toolkit URL (chart), image path (picture), or Excel path with driver/export ranges. |
| Cleaned template production | Complete | |
| Cleaned template as user-owned asset | Complete | Two edit tiers: cosmetic edits picked up silently on next run; structural edits require re-upload, which regenerates the Running Order. See Architecture Decision 2. |
| Template validation on run (slide layout comparison) | Complete | Compares slide layout names between the `.cgw` reference copy and the live template; warns on mismatch, doesn't block. See Architecture Decision 3. |
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
| `insert_chart` | Complete | Passes `ReportContext` for highlighting. |
| `empty_placeholder` | Complete | |
| `save_ppt` | Complete | |
| `save_pdf` | Complete | Disabled by default in generated Running Orders. |
| `set_default_populations` | Complete | Also read directly by the Charts tab to default its own preview populations string — a stopgap reading one Running Order row's value directly, not a general settings-reading mechanism. |
| `update_text` | Partial | See Text tag replacement, Part 5. |
| `insert_picture` | Complete | `[code]`/`[id]` token substitution; aspect ratio preserved. |
| Insert Content From Excel | Complete | Requires `pywin32`. Implemented via three functions: `open_excel`, `insert_from_excel`, `close_excel`. |
| `table_data_lift` | Not built | |
| Conditional Running Order logic (insert/delete slides per unit) | Not built | Needed for algorithmic reports. |
| `insert_slide` / `insert_section` / `delete_slide` | Not built | |
| `submission_list` | Not built | |

---

# Part 5 — Content Construction

## Chart construction

| Feature | Readiness | Notes |
|---|---|---|
| Base Chart library (20 charts across 4 data shapes) | Complete | No chart type renders a title. |
| TimeSeries chart rendering | Complete | Three chart types: `period_line_chart`, `median_comparison_linechart`, `full_lines_linechart`. Renders the first Metric-Series only. |
| Period selection / cutting (TimeSeries) | Not built | Every chart currently renders all periods; cutting to a single period or range is not yet built. |
| Populations string — Running Order control | Complete | |
| Reporting unit highlighting — NumericSeries (6 charts) | Complete | Selected can resolve to more than one unit, when the chart's own population table (`population_table` on the data shape) has a one-to-many relationship to the reporting unit — e.g. an organisation with several submissions. See Functional Spec Section 10.4. |
| Peer group as data filter (peer token leading the populations string) | Complete | Chart data scope narrows to the peer group; e.g. `Region(Wales)^Selected` shows Welsh units only. |
| Reporting unit highlighting — NumericCompositional | Not built | Per-unit values not currently in the data shape as returned from the API. |
| Reporting unit highlighting — CategoricalCompositional | Not applicable | These charts show population aggregates only; no per-unit value exists. |
| Reporting unit highlighting — TimeSeries | Complete | Selected unit(s) drawn as their own line(s); same one-to-many handling as other shapes. |
| Selection identity in autotable stats (all 20 charts) | Complete | |
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

## Tables

| Feature | Readiness | Notes |
|---|---|---|
| Text-tag-based table population (basic tables) | Not built | Depends on text tag replacement, which is built. |
| Autotables (statistics from chart construction) | Partial | Statistics are computed by the shape modules and collected at chart time, stored on `AssemblyContext` per `insert_chart`; the functions to populate a table from them are not yet implemented. |
| Multi-unit table expansion | Not built | |

---

## Text / variable content

| Feature | Readiness | Notes |
|---|---|---|
| Text tag replacement (`[org]`, `[region]` etc.) | Partial | Presentation-wide, single-pass, handles tokens split across runs. Table cells are not yet covered — `shape.table` cells are currently skipped. |
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
