# ChartGen — Functional Specification

*TBN Internal · Describes current behaviour only*

---

## 1. Purpose

Describes what ChartGen does and how it behaves — distinct from the Architecture document, which covers how it is built.

Covers the core report generation pipeline: data acquisition, chart construction, PowerPoint assembly, and batch processing. Features not yet built are noted where relevant; full scope is in the Feature List.

---

## 2. Design Principles

- **Package architecture** — packages interact through defined interfaces; swapping one package requires changes only within that package and its config.
- **Stable data contracts** — the Running Order passes canonical data structures to the Chart Engine regardless of charting library; chart type refs and tweaks are the Chart Engine's concern only.
- **Normalisation of chart data** — raw API data is normalised into one of four canonical shapes before any chart, table, or text function touches it. Chart type validity is enforced at authoring time.
- **PowerPoint is just the output format** — the system produces `.pptx`/`.pdf`; it does not distinguish use cases at output time.
- **Data is pre-fetched** — all data is fetched prior to output processing.
- **Outputs created only by Running Order functions** — each output is created by the functions specified on the Running Order. This is a complete set of instructions and not supported by any function not listed on the Running Order.
- **Function scope rule** — each Running Order function does only what its name describes — its internal sub-functions exist for that one purpose alone.

---

## 3. User Interface

The system is a desktop application launched via a `.bat` file. Double-clicking the launcher opens the Streamlit UI in the user's browser.

No login is required to launch the app or to create, open, edit, or save a workfile. Credentials are validated on demand from the Config tab (Section 3.2), via a single box: email (pre-populated once previously validated), password (entered manually, with a show/hide toggle), and a Validate button. Validation calls the API immediately and shows a confirmation message on success. On success, the username is written to `credentials.csv` for reuse next time; the password and session token are never persisted to disk — the token is held only for the session's duration. With no credentials validated, the only consequence is that Fetch (Section 7.1) fails until they are.

The Streamlit UI provides access to all workflow stages. Tab names follow a dual-naming convention: a short label displayed on the tab, and a full descriptive title as the page heading.

### 3.1 Sidebar File Operations

File operations sit in the sidebar, independent of the active tab; with no workfile open, tabs remain visible but empty. New Workfile, Open Workfile, Save, Save As, Save and Close, and Close Without Saving cover the full lifecycle. New Workfile triggers the New Workfile flow (Section 4); Save As prompts for a save location; Open Workfile and Close prompt to save first if the current workfile is dirty. Open Workfile leads to the file version compatibility check and concurrency decision step (Section 5) before a workfile loads.

### 3.2 Tab Structure

| Tab (short) | Tab (full) | Purpose |
|-------------|------------|---------|
| **Details** | Project Details | Read-only view of file identity and save history (file path, last saved by/at). No project identity shown — year/project/organisation are not workfile-level concepts once a workfile can hold more than one project's data (Section 7.2). |
| **Config** | User Controlled Configuration Files | Houses the single credentials box (Section 3). Management of reference CSVs and other runtime configuration files not yet implemented. |
| **Imports** | Import Project Data | Template upload and processing (Template Reader); the chart URL table (read-only view, edited via Excel download/upload); toolkit API fetch. |
| **Populations** | Populations | Every population table currently in the workfile, collapsible and reorderable. Whichever table sits on top (position 0) is the master table, driving the reporting unit picker and the batch loop — see Section 7.2. |
| **Select** | Reporting unit selection | Select an individual reporting unit from the master table, and see its Full Unit(s) — its own row plus every row related to it one hop out, across every population table. |
| **Text** | Text — Text Tags | Lists available text tags with a live preview of each tag's value for the currently selected reporting unit. |
| **Running Order** | Running Order (Output Script) | The master output script. Generated automatically from template processing. |
| **Charts** | Chart Preview | Preview and tune chart rendering; two-way sync with the Running Order (Section 9.3). |
| **Outputs** | Create Outputs | Run and monitor report generation. Preflight checks for template, Running Order, and unassigned chart types. Execution log per row. |

Tabs in scope for the final tool but not yet implemented are included as empty shells.

---

## 4. New Workfile Flow

Creating a new workfile collects a short description ("what is this workfile for?" — free text, for the person, not the system) and a save location/name via a single native Save dialog, then produces a genuinely blank `.cgw`: no project, no population tables, no toolkit involvement of any kind. The description is shown next to the ChartGen title in the app header for as long as the workfile stays open.

Population tables are added separately and automatically — see Section 7.2.

---

## 5. Opening a Workfile

### 5.1 File Version Compatibility

ChartGen tracks two independent version identifiers: the software id (this installed build of ChartGen) and the file version id (the `.cgw`'s internal structure, stamped into `workfile_info.json` at Save). A software update that changes no internal `.cgw` structure needs no file version change; a change to the `.cgw`'s internal structure needs a file version bump regardless of whether the software id changes.

Each build ships with a fixed list of file version ids it can read. Before the concurrency decision step (Section 5.2), the workfile's file version id is checked against that list. An incompatible file version id is a hard refuse — the workfile does not open, and no partial read or migration is attempted.

*Expanding compatibility (e.g. a build that can read and migrate an older file version) is not built.*

### 5.2 Concurrency

Locking is advisory only. Opening a workfile always leads to a decision step before it loads, naming one of three lock states and offering Open or Open Read-Only:

- not marked open by anyone;
- marked open by the current user — the prior session either did not close cleanly, or is still open elsewhere under the same account, indistinguishable from the lock alone;
- marked open by a different user, with their name and the time last marked open.

Choosing Open writes the lock and proceeds as a normal editable session — last-write-wins if two users both save. Choosing Open Read-Only opens the workfile without claiming the lock.

A Read-Only session disables Save only; every other action behaves as normal, so edits made are lost unless rescued via Save As. Save As from a Read-Only session must target a folder different from the original workfile's, to avoid two workfiles sharing an outputs folder, and converts the session to a normal editable one, writing the lock at the new location.

A crash or an uncleanly closed browser tab leaves the lock as last written; the next person to open the file sees this as the same decision step.

---

## 6. PowerPoint Templates

### 6.1 Template Files as Designed Artefacts

PowerPoint template files are produced separately from the ChartGen codebase — they are not generated by ChartGen. A template is a fully designed `.pptx` file with placeholders on each slide.

### 6.2 Placeholders as Element Slots

Each slide contains PowerPoint placeholders positioned and sized by the template designer. ChartGen recognises a placeholder by its native PowerPoint type — Content, Picture, Chart, Clip Art, Table, SmartArt, Media, or Text — not by its name; no naming convention is required. ChartGen reads each placeholder's name, position, and size directly from the `.pptx` file via the Template Reader. No separate coordinate config file is required — the template is entirely self-contained.

The Running Order references placeholders by name for display only; the system resolves coordinates from the template at generation time. A designer can reposition or resize a placeholder in the normal PowerPoint UI and the change is picked up automatically on next upload.

For charts, pictures, and tables, ChartGen uses the placeholder's coordinates as the insertion target. The placeholder itself is not used as a PowerPoint content container — ChartGen inserts content at those coordinates via python-pptx.

### 6.3 Yellow Textbox Convention

To associate content with a placeholder without editing any config file, the template designer places a yellow textbox fully inside the target placeholder. The Template Reader detects these textboxes and classifies each by its content.

Detection criteria — both must be true:

- **Yellow fill** — detected by colour, distinguishing human-placed yellow from cream, off-white, or pale gold.
- **Fully contained** — the textbox bounds lie entirely within a placeholder on the same slide.

Classification by content — one of three types:

- **Chart** — the text includes an NHS Benchmarking toolkit URL (or any HTTP URL as fallback). Any surrounding notes or labels are ignored.
- **Picture** — the text is a path to a supported image file; the path may contain `[code]`/`[id]` tokens.
- **Excel** — the text is an Excel file path plus driver and export range names.

Unrecognised content: the box is stripped with the others but otherwise ignored. One content source per placeholder is the contract. If multiple qualifying textboxes fall inside the same placeholder, the first is used and a warning is raised.

URLs extracted from chart-type boxes are merged into the chart URL table (`manifest.csv`) — new URLs added, existing ones preserved, and a URL matching a previously deleted row restores that row under its original identity. Template extraction never removes rows. No data is fetched at this point: the Running Order is generated immediately against the table, with each chart row's cache reference assigned; chart-type options are constrained once the data has been fetched and its shape is known.

### 6.4 Cleaned Template

After reading, the Template Reader strips all detected yellow textboxes from the template and saves a cleaned copy. The Assembly Engine works exclusively from the cleaned copy; the original is preserved. Yellow annotation boxes must never appear in output.

### 6.5 Template Validation

At run time, ChartGen compares the ordered list of slide layout names between the `.cgw`'s reference copy of the cleaned template and the live copy alongside the workfile. Matching lists proceed silently. A mismatch raises a warning naming which slides changed and how — soft, not blocking; the user can proceed or reprocess the template. Layout names are compared rather than slide count, since this catches slides added, removed, reordered, or reassigned to a different layout — all of which shift placeholder positions in the Running Order — while staying silent on cosmetic in-slide edits.

---

## 7. Data Acquisition

### 7.1 API Route (Primary)

Chart URLs enter the chart URL table (`manifest.csv`) by two routes: extraction from the template's yellow textboxes (Section 6.3), or direct entry by the user via the table's Excel download/upload round-trip — download the formatted `.xlsx`, add a row containing just a URL, and upload. Deleting a row in the Excel removes the chart from the table; its cached data and identity are retained, and re-adding the URL restores it.

Fetching is a single, explicit action on the Imports tab: a full refresh of every chart in the table, populating each row's title, project, service, year, and data shape as it goes. Data is fetched once and held in memory; no API calls occur during a batch run. The user can trigger a refresh at any point.

Every URL entering the chart URL table — whether extracted from a template or entered directly — is also classified by database ("nhs" or "indicators") at that point, decided from the URL's own path shape alone (`/outputs/{id}` vs `/project/{id}/toolkit`). This determines which toolkit's fetch pipeline processes the row at Fetch. See Section 7.4 for the Indicators toolkit's own pipeline.

Fetch requires a valid session token (Section 3); with none, it fails immediately with a message directing the user to the Config tab, rather than attempting per-row calls.

### 7.2 Population Tables

Population tables — `nhs_organisations` and any number of `submissions_{year}_{project_id}` tables — are the tables the system selects reporting units from and iterates over during a batch run. Every population table shares the same columns:

- **`unit_id`** — stable internal identifier for the row, within that table
- **`unit_code`** — outward-facing identifier; used for labels only, not relied on for logic
- **`unit_name`** — display name (e.g. trust name), used for labels and report titles
- **`soft_parents`** — this row's relationship links to other population tables (see below)
- any number of **`Name()`** peer-group columns

**Creation is automatic, not a user-facing action.** Nothing prompts for a project or year. During the toolkit fetch (Section 7.1), each chart's own `year`/`project_id` is identified from its URL; the first chart pulled for a project/year combination not already represented on the workfile triggers building that project's `submissions_{year}_{project_id}` table and merging its organisations into `nhs_organisations`. Every subsequent chart for the same combination is a no-op check. `nhs_organisations` is shared across every project a workfile holds — a further project's organisations are appended by `unit_id`, not overwritten; existing rows are untouched.

**Master table.** Whichever population table sits first in display order is the master table — it drives the reporting unit picker (Section 3.2, Select) and the batch loop (Section 13). Position is the only definition of "master"; there is no separate flag. Display order is user-changeable (Populations tab) and takes effect immediately.

**`soft_parents`.** A relationship between two population tables — e.g. a submission belonging to an organisation — is recorded on the child side only, as `table_name:id1^id2|table_name:id3` (`|` separates entries for different tables, `^` separates multiple ids within the same table). This is deliberately not called "parent": these relationships are not always one-parent-per-row (an organisation can support more than one ICB), so a row may hold zero, one, or several ids in a given table, and may link to any number of different tables at once.

**Resolving relationships.** Given a row, its related rows in other tables are resolved one hop only, in both directions: rows it links to via its own `soft_parents` (forward), and rows in other tables whose `soft_parents` link back to it (reverse, since the link is only ever recorded on the child side). The Select tab's Full Unit(s) view (Section 3.2) shows exactly this — a reporting unit's own row plus everything one hop out — and the same resolution is what a chart uses to find the correct unit(s) to treat as `Selected` in whichever population table its own data belongs to (Section 10.4). Resolution does not chain beyond one hop; a genuine multi-level hierarchy (e.g. Country→Region→ICB→Organisation→Submission→Ward) is not walked automatically — see Feature List.

Every peer group — however many named values it has, including a simple yes/no group — is a `Name()` column: the unit belongs to the named group its value states. A unit with no group for that column is marked `x` (or left blank) rather than assigned one; both are treated identically and excluded from the Running Order populations multi-select.

`Region()` is the first peer group column, resolved per organisation from `GET /organisations?year={year}` at the point a project's tables are built. Additional `Name()` columns can be added to any population table and will be picked up automatically by `build_population_layers` and the Running Order dialog without code changes.

Each population table is human-readable, editable in Excel, and uploadable via the Streamlit UI.

*Multi-level hierarchy model is not built. `soft_parents` covers one-hop relationships between any number of tables; a genuinely deep chain is not walked automatically.*

### 7.3 Data Cache

The data cache is a folder containing one JSON file per fetched chart, named by the chart's `hex_id`, plus the manifest table (`manifest.csv`) indexing every chart in the workfile — URL, title, database, project, service, year, data shape, source, and fetch timestamps. It is written exclusively by Data Acquisition; the Chart Engine, tables, and text replacement all read from it. A chart removed from the table keeps its cached data under its reserved identity.

### 7.4 Indicators Toolkit Data Acquisition

Chart URLs classified as "indicators" (Section 7.1) are fetched via a separate API (`icsapi.nhsbenchmarking.nhs.uk`), sharing the same credential/token as the NHS toolkit (Architecture Decision 7) — no separate login or credential set is needed.

Each fetch makes two report-level calls (report details, for title and format hint; report data, for the full per-period, per-organisation dataset) plus one project-level submissions call (`/projects/{id}/submissions`), which supplies the project's visible-dates list alongside a live organisation-id mapping and real submission names in the same response (see below). This call is cached once per project for the duration of a single Fetch run, rather than repeated once per row.

Only periods the project's visible-dates list marks as available (`outputAvailability <= today`) are kept. The API's own period ordering is trusted as chronological and is not re-sorted.

Data transforms into a TimeSeries shape (Section 8.2). The API's own per-period averages, medians, and national-average figures are discarded entirely at this step — stats are recomputed locally per period instead, the same way every other shape computes stats against a resolved population layer, just applied once per period rather than once for the whole shape.

The population table (`submissions_timeseries_{project_id}`) is merged on every fetch, not built once and skipped thereafter (contrast Section 7.2's NHS model) — a single response already spans a project's full period history, and submissions genuinely drop in and out of the population over time. Each submission's organisation link is resolved via a live mapping (ics `organisationId` → nhs `unit_id`), taken from the same project-level submissions call above — confirmed as necessary, since the two databases' organisation id spaces do not match. A submission whose organisation has no entry in that mapping is still added, with no organisation link and `Region()` left blank; a single warning is surfaced once fetching completes, not per submission. A newly-resolved organisation not yet in `nhs_organisations` is enriched from the NHS organisations endpoint (Section 7.2, queried against the current calendar year — Indicators data has no year of its own) for its canonical name and `Region()`, falling back to the Indicators response's own values only if that organisation isn't present in that year's NHS list. Submission `unit_name` is taken from the same project-level call's real submission name, rather than the anonymised code used for `unit_code`.

---

## 8. Data Shapes

### 8.1 Purpose

Chart data is normalised into a small set of canonical data shapes. All downstream consumers — the Chart Engine, tables, text replacement — work exclusively against these normalised shapes.

**Immutability.** A data shape instance is never modified in place. Filtering, narrowing, or recalculating against one — including `build_population_layers` producing a population-filtered copy — always creates a new copy, leaving the original untouched. This avoids two risks: incompatible edits building up on a shared instance, and edits being silently forgotten because nothing marks that a change happened.

**`population_table`.** Every data shape carries the name of the population table its units belong to (e.g. `submissions_2026_123`), set once at fetch from the chart's own URL — not derived at read time, and not necessarily the workfile's current master table. This is what lets `insert_chart` (Section 10.4) resolve the correct table and correct unit(s) for `Selected` on a per-chart basis, rather than assuming every chart's population is the master table.

### 8.2 Canonical Data Shapes

Four shapes are implemented — three matching the stored procedure groups present in the TBN NHS API, plus TimeSeries, which comes from the separate Indicators toolkit API (Section 7.4) instead:

| Shape | Description |
|-------|-------------|
| **NumericSeries** | One or more independent numeric Metric-Series. One value per unit per metric. |
| **NumericCompositional** | One or more Metric-Series whose Component-Series sum to a whole (e.g. radar/spider chart data). |
| **CategoricalCompositional** | One or more Metric-Series (questions) with categorical Component-Series summing to a whole (e.g. yes/no, ethnicity breakdown). |
| **TimeSeries** | One or more independent numeric Metric-Series, one value per unit per metric per period, across a period axis shared by every Metric-Series in the shape. |

Every shape carries flags indicating where its data is incomplete, so consumers know upfront which operations aren't possible rather than discovering it at build time.

### 8.3 Data Shapes and Chart Type Validity

Each chart type reference in the Chart Engine declares the data shape(s) it accepts. The Running Order editor uses this to constrain chart type options to valid combinations for the selected data. Invalid pairings — a bar chart against compositional data, a radar chart against a single-metric dataset — are prevented at authoring time rather than discovered at batch runtime.

TimeSeries has three (`period_line_chart`, `median_comparison_linechart`, `full_lines_linechart`) — it fetches, caches, and renders correctly. Cutting to a single period or range is not yet built; every chart currently renders all periods — see Feature List.

---

## 9. Report Assembly

### 9.1 Running Order

The Running Order is the master script that drives report assembly — a sequential list of rows, each specifying:

- **Function** — the name of the function to call
- **Parameters** — placeholder name, chart type reference, cache file, EMU position/size, etc.
- **Enabled column** — enables rows to be switched on/off without deletion

Each row name maps in a strict 1:1 relationship to a single callable function. A row can never invoke multiple functions, and a given row name can never resolve to different functions. There is no conditional dispatch, no indirection. This is not a constraint — it is what makes the Running Order legible: any colleague can read it and know exactly what will happen, line by line.

Outputs are generated by processing the functions on the Running Order.

Generated Running Orders follow a standard structure: any `open_excel` rows (scope `batch_open`) first; then `create_ppt`, `set_default_populations` (defaulting to `All^Selected`), and `update_text`; one row per placeholder, resolved by yellow-box classification (`insert_chart`, `insert_picture`, `insert_from_excel`, or `empty_placeholder`); then `save_ppt` and `save_pdf` (disabled); and finally any `close_excel` rows (scope `batch_close`).

An `.xlsx` version can be generated by the system as a human-editing format for the Running Order — created on demand for download and parsed back in on upload. It is never written to disk on its own and never persisted inside the `.cgw` itself. Dropdown validation constrains `function`, `enabled`, and `chart_type_ref` (per-row, filtered to valid chart types for the assigned cache file's data shape) on each export. It is editable directly in Excel and uploadable/downloadable via the Streamlit Running Order tab.

### 9.2 Running Order Functions (Current Scope)

| Function | Description |
|----------|-------------|
| `create_ppt` | Opens the cleaned template; sets the output path. Always the first per-report row. |
| `set_default_populations` | Sets the workfile-default populations string, applied to any `insert_chart` row without a per-row override. |
| `insert_chart` | Renders a Base Chart from cached data; inserts at the named placeholder position. Position and size come from the Running Order row, populated automatically from the template. |
| `empty_placeholder` | No-op. Placeholder has no content assigned. Explicit so every placeholder is accounted for. |
| `save_ppt` | Saves the completed output as `.pptx`. |
| `save_pdf` | Saves the completed output as `.pdf` via COM automation (requires PowerPoint on the user's machine). Disabled by default in generated Running Orders. |
| `insert_picture` | Inserts an image at the named placeholder, with `[code]`/`[id]` token substitution in the source path and aspect ratio preserved. |
| `update_text` | Replaces text tags in template text with per-unit values, presentation-wide, single-pass. Partial — table cells (`shape.table`) are not yet covered. |
| `open_excel` / `insert_from_excel` / `close_excel` | Excel COM capture: writes `unit_id` to the driver range, recalculates, and captures the export range as an image. Requires `pywin32`. |

*`insert_slide`, `insert_section`, `delete_slide`, `submission_list`, and `table_data_lift` are not built.*

### 9.3 Charts Sheet Round-Trip

The Charts sheet provides two entry points into a chart's specification, always interchangeable: loading an existing `insert_chart` Running Order row, or loading a cached dataset directly with no row bound. Editable fields are `chart_type_ref`, `cache_file`, `populations`, `width_emu`, and `height_emu` — a fixed set (`CHART_SANDBOX_FIELDS`, see Architecture) rather than the full row schema. Position (`left_emu`/`top_emu`), slide/placeholder assignment, and scope are never touched from this sheet.

Width and height are authored as a percentage of the shorter dimension of the associated PowerPoint page (Section 9.4) rather than as raw EMU, converting to EMU only at the point of writing back.

Saving offers three actions: overwrite the bound row's fields in place, or insert a new row (copied from a target row, with the edited fields applied on top) immediately above or below it. Target row selection is independent of how the sheet was entered — a directly-loaded dataset with no bound row must have a target chosen explicitly.

### 9.4 Page Size Capture

A workfile records the associated PowerPoint template's slide width and height once, at template processing, alongside the cleaned template asset. This is the reference dimension for the percent-of-shorter-dimension sizing unit (Section 9.3). Before any template has been processed, a manual choice from a small set of standard page sizes stands in for this value.

---

## 10. Chart Construction

### 10.1 Chart Type References

Each chart is identified in the Running Order by a **chart type reference** (e.g. `ranked_column`). This reference resolves via `chart_type_map.csv` to a specific Base Chart function. Chart type references are reusable across projects.

The system supports all four canonical data shapes — NumericSeries, NumericCompositional, CategoricalCompositional, and TimeSeries — with 20 Base Chart functions across them.

### 10.2 Base Chart Library

| Shape | chart_type_ref | Description |
|-------|---------------|-------------|
| NumericSeries | `ranked_column` | Ranked descending column with mean/median/quartile lines |
| NumericSeries | `dot_strip` | Strip plot — one dot per organisation |
| NumericSeries | `box_whisker` | Box and whisker with outliers |
| NumericSeries | `frequency_histogram` | Frequency histogram |
| NumericSeries | `violin_plot` | Violin / KDE distribution |
| NumericSeries | `bead_string_dot_plot` | Multi-tier bead string — one tier per population layer |
| NumericCompositional | `ugly_bar` | Horizontal bar — component breakdown |
| NumericCompositional | `radar_chart` | Radar / spider chart |
| NumericCompositional | `donut_component` | Donut chart — component proportions |
| NumericCompositional | `lollipop_chart` | Lollipop — stem and dot per component |
| NumericCompositional | `waffle_chart` | Waffle — 10×10 grid, each cell ≈ 1% |
| CategoricalCompositional | `yn_bar` | Horizontal stacked Yes/No bar |
| CategoricalCompositional | `list_pie` | Pie chart with leader line labels |
| CategoricalCompositional | `diverging_bar` | Diverging bar — Yes right / No left from centre |
| CategoricalCompositional | `dot_matrix` | Dot matrix — filled dots per category per question |
| CategoricalCompositional | `donut_pie` | Donut ring chart |
| CategoricalCompositional | `treemap` | Area-proportional category rectangles |
| TimeSeries | `period_line_chart` | Population mean/IQR band across every period, Selected/peer lines on top |
| TimeSeries | `median_comparison_linechart` | Median per population layer across every period; Selected shows actual value(s) |
| TimeSeries | `full_lines_linechart` | Every unit in the largest population as a light grey line, Selected/peer lines on top |

No Base Chart renders a title.

`bead_string_dot_plot` additionally de-duplicates visually across its tiers: a unit already shown in a more specific (later-token) tier is suppressed from every broader (earlier-token) tier's dots, so e.g. the `Selected` unit(s) appear once, in the `Selected` tier, rather than also as a dot in `Region()` and `All`. This affects only which dots are drawn — the reference statistics (mean/median/quartiles) and the value shown for `Selected` are computed independently of the suppression.

### 10.3 Tweaks

*All tweaks are not built.*

### 10.4 Population Layers and Chart Data Flow

Charts do not receive a single data shape. They receive an ordered list of filtered copies of the data shape, one per population token in the populations string, each carrying a `population_label` field naming its layer (e.g. `"All"`, `"Selected"`, or a resolved peer-group value).

**The populations string** (e.g. `All^Region()^Selected`) is specified on the Running Order — either as a workfile default via `set_default_populations`, or overridden per chart row in the `populations` column. It is authored as a `^`-delimited ordered list of tokens and edited via a multi-select in the Running Order dialog.

**Resolution — scope-plus-independent-layers model:** `build_population_layers` treats the first token as the scope — the full set of units the chart compares. Every subsequent token resolves independently against that scope, not against each other:

1. Resolve the first token against all units in the data shape; this becomes the scope. An unresolvable or empty first token produces no population layers.
2. Resolve each remaining token against the scope only; unresolvable tokens are skipped.
3. Filter the data shape to each result; recalculate stats against that population.
4. Set `population_label` to the resolved label and append, in token order.

**Which table `Selected` and the peer-group columns resolve against.** A chart's data belongs to one population table (`population_table` on the data shape, Section 8) — not necessarily the workfile's current master table. Before resolving any token, the Assembly Engine looks up that table's rows, and looks up the current reporting unit's Full Unit Set (Section 7.2) for that same table. `Selected` resolves to whichever unit(s) the Full Unit Set holds for that table — which may be none, one, or several: an organisation-level chart, for a reporting unit selected from a submissions table, resolves to that submission's one organisation; an organisation selected as the reporting unit, charted against a submissions table, resolves to every submission linked to it. More than one unit is intended behaviour where the relationship is genuinely one-to-many, not a case to collapse to a single value.

`Selected` is a layer like any other. Peer tokens support both empty-bracket form (`Name()`, the selected unit's own group — where more than one unit is selected, one is used as the representative for this lookup) and explicit-value form (`Name(Value)`, a named group, which need not contain the selected unit).

**Token position determines scope vs. layer.** The first token is always the scope; everything after it is an independent layer within that scope. `Region()^Selected` scopes to the selected unit's own region — the wider population never appears. `All^Region()^Selected` scopes to everyone, with region and Selected as layers inside it.

**Example:** `Region(Wales)^Hospital_Size()^Selected` produces three shapes: (1) all Welsh units — the scope; (2) the selected unit's hospital-size group, resolved within Wales; (3) the selected unit, resolved within Wales. Layers 2 and 3 are independent of each other, not cumulative.

The canonical data shapes are designed to hold any comparative analysis dataset; the Chart Engine's contract with the Running Order means any chart type Python's libraries can render can be added without changes elsewhere in the system.

### 10.5 Autotables

Autotable statistics are computed by the shape modules and merely collected at chart time — counts, distribution statistics, and component values with their percentages, independent of which chart renders the data. Each `insert_chart` stores the scope shape's statistics on `AssemblyContext`. This data flow is in place; the functions to populate a table from these statistics are not yet implemented — partial.

### 10.6 Chart Sizing

Charts are sized to their placeholder dimensions. The Running Order stores placeholder width and height in EMU (captured from the template by the Template Reader). The Assembly Engine scales the rendered chart to those dimensions and inserts it at the exact EMU coordinates. The Charts sheet offers a percent-of-page-size alternative to authoring these values directly — see Section 9.3.

---

## 11. Tables

### 11.1 Text-Tag-Based Tables

Tables built in the PowerPoint template are populated via text tag replacement at generation time.

### 11.2 Autotables

See 10.5.

*Multi-unit table expansion is not built.*

---

## 12. Text and Variable Content

Variable text is managed via text tags embedded in the template (e.g. `[org]`, `[region]`). At generation time, tags are replaced with the correct value for the current reporting unit.

The presentation is walked per report at generation time: every text frame is checked and tags replaced with the current reporting unit's values. Replacement operates at paragraph level, so tags split across text runs by PowerPoint's XML are still caught.

*Conditional text (formula-driven tag values) is not built.*

---

## 13. Batch Processing

**Run Selected** executes the Running Order once, against the currently selected reporting unit. **Run Batch** executes the Running Order once for each of the next N reporting units in the queue, starting from the batch cursor. **Run All** executes the Running Order once for every reporting unit in the population. The batch loop's role is limited to iteration; report construction itself is the Assembly Engine's responsibility (Section 9).
