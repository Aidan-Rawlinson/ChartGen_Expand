# ChartGen — Feature List

*TBN Internal · Input document for refactoring — describes current scope and readiness only*

**Readiness** — Complete (confirmed built and working) · Partial (implemented but with a known gap, noted below) · Not built (no implementation yet)

Structured in pipeline order: application/session foundations, then workfile setup, data acquisition, template and report definition, content construction, execution, and output.

---

# Part 1 — Application & Session Foundations

## Credentials & authentication

| Feature | Readiness | Notes |
|---|---|---|
| Login validates against API before proceeding | Complete | |
| Multiple database support | Not built | Different TBN databases require different credentials. Not every TBN project is on a different database, so this is a database-level gap, not a workfile-level one. |

---

## Workfile / file structure

| Feature | Readiness | Notes |
|---|---|---|
| `.bat` launcher | Complete | |
| Workfile file format (`.cgw`) | Complete | See Architecture document. |
| Concurrency via `workfile_info.json` lock fields | Partial | See Architecture Decisions 4–6. The lock itself remains advisory and is not re-checked after Open. |
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
| File association (double-click a `.cgw` file to open ChartGen) | Not built | Requires an installer; no installer exists. |
| Custom icon for `.cgw` files | Not built | Requires an installer; no installer exists. |

---

# Part 2 — Workfile Setup

## Workfile setup

| Feature | Readiness | Notes |
|---|---|---|
| New Workfile flow (year → project → save location) | Complete | See Functional Spec Section 4. |
| Year selectbox | Complete | |
| Project dropdown (API-populated, cached per year) | Complete | |
| Submissions fetch at workfile creation | Complete | An invalid year/project combination blocks creation. |
| Details tab (read-only project settings) | Complete | |

---

## Select

| Feature | Readiness | Notes |
|---|---|---|
| Select tab — reporting unit selectbox (name / code / ID) | Complete | |
| Select tab — Populations section | Complete | |

---

# Part 3 — Data Acquisition

## Data acquisition

| Feature | Readiness | Notes |
|---|---|---|
| API route (toolkit URL → data fetch → store) | Complete | Primary data source. |
| Manual data entry / in-system analysis | Not built | Supplementary route; not currently used. |

---

## Reference / supporting data

| Feature | Readiness | Notes |
|---|---|---|
| Reporting units + identifiers | Complete | Fetched from API at workfile setup; stored as `units.csv`. |
| Peer group assignments — `Region()` | Complete | Resolved at workfile creation, written permanently into `units.csv`. |
| Additional peer group columns (`Name()`) | Complete | Both empty-bracket (`Region()`, the selected unit's own group) and explicit-value (`Region(Wales)`, a named group) tokens are supported end-to-end: column discovery, Running Order multi-select (auto-populated with every distinct value per column), and resolution against the population scope. Blank and `x` values are excluded from discovery and treated as no group. |
| Multi-level hierarchy model | Not built | Current model uses a single flat population. |

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
| `set_default_populations` | Complete | |
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
| Base Chart library (17 charts across 3 data shapes) | Complete | |
| Populations string — Running Order control | Complete | |
| Reporting unit highlighting — NumericSeries (6 charts) | Complete | |
| Peer group as data filter (peer token leading the populations string) | Complete | Chart data scope narrows to the peer group; e.g. `Region(Wales)^Selected` shows Welsh units only. |
| Reporting unit highlighting — NumericCompositional | Not built | Per-unit values not currently in the data shape as returned from the API. |
| Reporting unit highlighting — CategoricalCompositional | Not applicable | These charts show population aggregates only; no per-unit value exists. |
| Selection identity in autotable stats (all 17 charts) | Complete | |
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
