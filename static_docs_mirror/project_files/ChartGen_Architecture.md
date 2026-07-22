# ChartGen — Architecture

*TBN Internal · Describes the current system only*

---

## 1. Purpose and Scope

Describes how ChartGen is built: its structure, the format of its data at rest and in memory, and the technical decisions that govern it.

---

## 2. Structural Design Principles

*Principles governing project structure, package and module layout, and naming, not the code within files. Distinct from the Primer's design-intent principles (Section 4 there), which govern how data and logic behave.*

ChartGen was built rapidly as a proof of concept. Its project structure is the strongest, and in places the only, record of what the system is meant to be doing, so structural decisions carry more weight here than they would in a more conventionally documented codebase.

| Principle | What it means |
|---|---|
| Separation of concerns | Each package owns one job. If the job cannot be stated in a sentence, it is not one package. |
| Legibility | Structure is the documentation. A reader should learn what the system does from folder and file names alone, without reading code. |
| High cohesion, low coupling | Things that change together live together. Things that do not need each other do not import each other. |
| Explicit, one-way dependencies | No hidden reach-through, no circular imports. The dependency graph can be drawn as an arrow diagram with no loops. |
| Conventional Python layout | Standard `__init__.py`, import, and naming conventions. Software domain only; the Workfile domain is a data format, not Python code. |
| Intention-revealing names | A name states the decision the package exists to make, not just what is inside it. |
| Deliberately fine-grained | Finer than default Python convention recommends, because structure carries information here that would otherwise live nowhere (Legibility, Intention-revealing names) and more packages and modules mean more chances to name things. Bounded by Separation of concerns: a split still needs its own reason to exist. |
| Moderate, meaningful nesting | Depth encodes relationship, not just size. A sub-package states that it belongs to its parent and is its own concern within it. One flat layer loses that relationship; four or more layers makes the tree illegible. Each layer needs the same justification as a whole package: a real parent-child relationship, not a package that felt big. |

**Scope.** Applies to the Software domain's package and module layout (Section 4) and to the Workfile domain's on-disk layout, the `.cgw` internal structure (Section 5) — one system, separated into two domains for functional reasons only. Conventional Python layout does not apply to the Workfile domain.

---

## 3. Two Domains

ChartGen's data exists in two separate places, each with its own lifecycle, format, and rules about what may live there.

| Domain | What it is | Lifecycle | Format |
|---|---|---|---|
| **Software** | The installed application — code, static config, per-machine settings | Persists across every project and session until reinstalled or updated | Python source, CSV (static config), one small per-machine CSV (username) |
| **Workfile** | A single workfile's complete footprint — the `.cgw` file, its sibling `.pptx` and `outputs/` folder, and, while open, the in-memory working copy of all of it | The `.cgw`/`.pptx`/`outputs/` persist once saved and are shareable; the in-memory copy exists only between Open and Close/crash, discarded if not saved | `.cgw` (ZIP), sibling `.pptx` and `outputs/` folder on disk; Python objects — dataclasses, dicts, lists — in memory when open |

Memory isn't a third place workfile data lives — it's the Workfile domain's in-session form, the working copy of what's on disk. It gets its own walkthrough below (Section 6) because its structure differs enough from the on-disk layout to warrant one, not because it's conceptually separate.

**Defining rule:** the Software domain doesn't change as a result of workfile work. Opening a workfile, fetching data, editing the Running Order, running batches — none of it touches the installed application, the same way writing a letter in Word doesn't change Word itself. The Software domain changes only as a function of *which user is logged in on this machine*, never as a function of *what workfile work was done*. The one exception (last-used username) is documented under Decision 7.

---

## 4. Software Domain

The installed application folder. Identical on every machine running the same version of ChartGen; never contains workfile data.

```
chartgen/
├── app.py
├── run_chartgen.bat
├── requirements.txt
├── user_resources/
│   └── PPT_Template_Creation.md
└── core/
    ├── session_shell/
    │   ├── auth/
    │   │   ├── login.py
    │   │   └── credentials.csv
    │   └── lifecycle/
    │       └── concurrency.py
    ├── workfile/
    │   ├── setup/
    │   │   ├── new_workfile.py
    │   │   └── save_as.py
    │   └── state/
    │       ├── workfile_file.py
    │       └── session_state.py
    ├── acquisition/
    │   ├── import_flow.py
    │   ├── url_triage.py
    │   ├── fetch_dispatch.py
    │   ├── manifest_table/
    │   │   ├── xlsx_writer.py
    │   │   └── xlsx_reader.py
    │   ├── toolkit_nhs/
    │   │   ├── api_client.py
    │   │   ├── fetch.py
    │   │   ├── transformers.py
    │   │   ├── peer_groups.py
    │   │   ├── population_tables.py
    │   │   └── table_naming.py
    │   ├── toolkit_indicators/
    │   │   ├── api_client.py
    │   │   ├── fetch.py
    │   │   ├── url_parser.py
    │   │   ├── transformers.py
    │   │   ├── population_tables.py
    │   │   └── table_naming.py
    │   └── template/
    │       ├── template_reader.py
    │       └── url_parser.py
    ├── output_generation/
    │   ├── static_config/
    │   │   └── chart_type_map.csv
    │   ├── definition/
    │   │   └── running_order/
    │   │       ├── schema.py, dialog_support.py, generation.py, row_ops.py,
    │   │       └── xlsx_writer.py, xlsx_reader.py
    │   └── execution/
    │       ├── assembly_engine.py
    │       ├── batch_process.py
    │       ├── results.py
    │       ├── charts/
    │       │   ├── base_charts/
    │       │   │   ├── shared.py, numeric_series.py, numeric_compositional.py,
    │       │   │   └── categorical_compositional.py, timeseries.py, registry.py
    │       │   ├── cache_reader.py
    │       │   └── chart_type_map.py
    │       ├── pictures/
    │       │   └── insert_picture.py
    │       ├── excel/
    │       │   └── insert_from_excel.py
    │       └── text/
    │           └── text_engine.py
    ├── shared/
    │   ├── normalisation_containers/
    │   │   ├── shapes/
    │   │   │   ├── common.py, numeric_series.py, numeric_compositional.py,
    │   │   │   └── categorical_compositional.py, timeseries.py, dispatch.py
    │   │   ├── population_layers.py
    │   │   ├── peer_group_tokens.py
    │   │   └── shape_transforms.py
    │   └── infrastructure/
    │       ├── constants.py
    │       ├── report_context.py
    │       ├── soft_parents.py
    │       ├── page_sizing.py
    │       ├── cache_writer.py
    │       └── population_table_xlsx.py
    └── ui/
        ├── common/
        │   ├── formatting.py
        │   ├── pickers.py
        │   ├── guidance.py
        │   └── layout_css.py
        ├── auth/
        │   └── login_form.py
        ├── workfile/
        │   ├── sidebar.py, workfile_dialogs.py, new_workfile_form.py,
        │   └── open_workfile_form.py, save_as_form.py
        └── tabs/
            ├── imports_tab.py, populations_tab.py, select_tab.py,
            └── text_tab.py, running_order_tab.py, charts_tab.py, outputs_tab.py
```

| Path | Notes |
|---|---|
| `app.py` | Streamlit entry point — sequences the sign-in gate, startup workfile check, sidebar, dialogs, and tabs; holds no UI construction or business logic of its own. The sign-in gate is the first thing rendered — see Decision 7 |
| `run_chartgen.bat` | Double-click launcher; creates venv on first run |
| `requirements.txt` | Python dependencies (kept in sync with `.bat`) |
| `user_resources/PPT_Template_Creation.md` | Guidance doc for template designers |
| `core/session_shell/auth/` | Credential validation, token handling, last-used-username persistence (mechanics only). `credentials.csv` is ★ the one genuine exception to the software/workfile split, see Decision 7 |
| `core/session_shell/lifecycle/concurrency.py` | Lock-state classification and Open/Open Read-Only mechanics for the workfile advisory lock |
| `core/workfile/setup/new_workfile.py` | The New Workfile flow's file-creation half only — a blank `.cgw`, the description field, session settings scaffold. No project, no NHS toolkit involvement, no population tables of any kind |
| `core/workfile/setup/save_as.py` | Save Workfile As — cleaned-template copy, lock transfer/release, and the read-only-session-must-choose-a-different-folder rule |
| `core/workfile/state/workfile_file.py` | Owns the `.cgw` format — see Section 5. The only module that reads/writes the ZIP directly. Population tables have no single fixed column schema here — each is written using its own rows' keys; the shared spine (Section 5) is a convention followed by whichever module builds a table's rows, not a schema enforced here |
| `core/workfile/state/session_state.py` | Streamlit-side `WorkfileState` accessors — Streamlit-rerun plumbing only |
| `core/acquisition/import_flow.py` | Coordinator: sequences template read → URL merge into the manifest table → Running Order generation. Data fetching is not part of this sequence — the single fetch process is the Imports tab's Fetch action. The only module that imports both `acquisition` and `output_generation.definition` |
| `core/acquisition/url_triage.py` | `url_to_database` — classifies a chart URL as `"nhs"` or `"indicators"` by path shape alone, called at manifest-row creation (both `import_flow.py` and `manifest_table/xlsx_reader.py`), before either toolkit's own URL parsing runs. See Decision 10 |
| `core/acquisition/fetch_dispatch.py` | Combines every toolkit's own `fetch_all` into the single Fetch action the Imports tab calls, reporting progress as one continuous total across both. Lives outside both toolkit packages for the same reason `url_triage.py` does — something has to know about both without either depending on the other. See Decision 10 |
| `core/acquisition/manifest_table/` | Excel export/import round-trip for the manifest table (`data_cache/manifest.csv`) — the acquisition-side equivalent of the Running Order's xlsx pair. Schema ownership stays with `workfile_file` |
| `core/acquisition/toolkit_nhs/` | Fetch → canonical data shapes (API client, transformers, peer-group menu-building), plus population table construction (`population_tables.py`) and table-naming convention (`table_naming.py`). Lives here, not in `workfile.setup`, because building population tables is a "pull and normalise NHS toolkit data" concern, the same kind of thing as the rest of this package — and because `fetch.py` (same package) needs to call it directly without acquisition code depending on `workfile.setup` (one-way dependency rule, Section 2) |
| `core/acquisition/toolkit_indicators/` | The Indicators toolkit's own fetch pipeline — separate API, separate URL shape, separate population-table trigger model from `toolkit_nhs/` (build-once vs merge-every-fetch). Shares NHS's token (`toolkit_nhs.api_client.get_token`) and reuses `toolkit_nhs.api_client.get_organisations` for organisation enrichment, plus the shared `cache_writer` — see Decision 10 |
| `core/acquisition/template/` | Reads `.pptx` placeholders; detects yellow boxes and resolves each against the slide's placeholders into three outcomes — contained, free-floating, or ambiguous overlap (see Decision 13); parses toolkit URLs |
| `core/output_generation/definition/running_order/` | Split by concern: schema (`schema.py`), row-edit dialog support (`dialog_support.py`), template-generation (`generation.py`), generic row insert/overwrite operations (`row_ops.py`, used by the Charts sheet's save-back control), and `.xlsx` export/import (`xlsx_writer.py`, `xlsx_reader.py`). Package `__init__.py` re-exports the full API, so external call sites are unaffected |
| `core/output_generation/execution/assembly_engine.py` | Executes one report's normal-scope Running Order rows via dispatch table. Not the only module touching `python-pptx` — `insert_picture` and `insert_from_excel` also do |
| `core/output_generation/execution/batch_process.py` | Batch loop — splits enabled Running Order rows by scope (`batch_open`/`normal`/`batch_close`) and iterates `assembly_engine.run_running_order` across the units in a run |
| `core/output_generation/execution/results.py` | `ok_result` / `err_result` — kept local to `execution`, not shared globally |
| `core/output_generation/execution/charts/` | 20 Base Charts, split into `base_charts/` by canonical data shape (`numeric_series.py`, `numeric_compositional.py`, `categorical_compositional.py`, `timeseries.py`), with shared palette/helpers in `shared.py` and dispatch in `registry.py`; cache reading |
| `core/output_generation/execution/pictures/insert_picture.py` | `insert_picture` Running Order function |
| `core/output_generation/execution/excel/insert_from_excel.py` | Excel COM capture (`open_excel` / `insert_from_excel` / `close_excel`) |
| `core/output_generation/execution/text/text_engine.py` | `update_text` Running Order function — promoted out of `assembly_engine` to its own module |
| `core/output_generation/static_config/chart_type_map.csv` | Data shape → valid chart type refs (developer-owned, read-only) |
| `core/shared/normalisation_containers/` | NumericSeries / NumericCompositional / CategoricalCompositional / TimeSeries, split into one module per shape under `shapes/`, each owning its shape's canonical Metric-Series stats computation and autotable statistics (plus `common.py` for the shared `Unit`/`ShapeStats` base and `dispatch.py` for `filter_shape`/`autotable_stats`/`apply_period_range`); `build_population_layers`; the shared peer-group token rule; `shape_transforms.py` for cross-shape conversions (see Decision 12) |
| `core/shared/infrastructure/constants.py` | `coerce_row` / `FIELD_TYPES` — generic CSV/WorkfileState field-type coercion, used by `api_client`, `running_order`, and `workfile_file`; also `SPINE_COLUMN_ORDER`, the population-table spine's display/authoring column order, shared between the UI and the Excel round-trip below |
| `core/shared/infrastructure/report_context.py` | `ReportContext` + `build_report_context()` |
| `core/shared/infrastructure/soft_parents.py` | `format_soft_parents` / `parse_soft_parents` / `resolve_related_rows` / `resolve_referencing_rows` / `resolve_all_related_rows` / `resolve_full_unit_set` — the `soft_parents` relationship format and its one-hop resolution, both directions. Generic across any population table, not NHS-specific |
| `core/shared/infrastructure/page_sizing.py` | `percent_to_emu` / `emu_to_percent` / `get_page_size_emu` / `has_known_template_page_size` — conversion between EMU and a percent-of-shorter-page-dimension unit, and resolution of which page size to convert against (the real captured template size once known, a manual standard-size fallback otherwise). Used by the Charts sheet only; has no bearing on batch execution, which continues to work in raw EMU throughout |
| `core/shared/infrastructure/cache_writer.py` | `save_chart` — serialises any canonical data shape into `WorkfileState.cache`. Moved here from `acquisition/toolkit_nhs/` this session: audited as having no NHS-specific logic at all, so it's shared by both toolkit packages rather than duplicated. See Decision 10 |
| `core/shared/infrastructure/population_table_xlsx.py` | Excel export/import round-trip for any population-level table — the workfile-state equivalent of the manifest table's own xlsx pair (`acquisition/manifest_table/`). Generic across any table's own columns; identity is `unit_id`, not a system-generated key |
| `core/ui/` | Streamlit UI, grouped into `common/` (generic display/picker helpers, per-tab guidance links, layout CSS), `auth/` (the page-level sign-in gate), `workfile/` (sidebar, dialogs, New/Open/Save As forms), and `tabs/` (the seven tab renderers). Business logic delegated to the owning module rather than living here |

---

## 5. Workfile Domain — On Disk (`.cgw`)

A single workfile's complete, portable, shareable state. Internally a ZIP archive — the same pattern as `.pptx`, `.docx`, `.xlsx`.

```
MyWorkfile.cgw  (ZIP)
├── workfile_config/
│   ├── settings.csv
│   ├── tables/
│   │   └── {table_name}.csv
│   └── running_order.csv
├── data_cache/
│   ├── manifest.csv
│   └── {hex_id}.json
├── template/
│   └── MyWorkfile.pptx
└── workfile_info.json
```

| Path | Notes |
|---|---|
| `workfile_config/settings.csv` | key,value — paths, `table_order`, `batch_cursor`, workfile description, `template_page_width_emu`/`template_page_height_emu` (captured once at template processing — see Decision 11), etc. Deliberately holds no project identity (no year, project_id, project_name) — a workfile can span more than one project, so none of those are workfile-level facts any more; see the shared spine below for where project/year identity actually lives |
| `workfile_config/tables/{table_name}.csv` | ★ One file per population-level table (e.g. `nhs_organisations.csv`, `submissions_2026_123.csv`) — any number of them, added and removed freely. No single fixed column schema at this layer; each is written using its own rows' keys. `table_order` (in `settings.csv`, `\|`-delimited) is the only record of display order — whichever table name is listed first is the master table, driving the reporting unit picker and the batch loop. No separate "master" flag exists; position is the only source of truth |
| `workfile_config/running_order.csv` | ★ Canonical Running Order store — flat table, not `.xlsx`. The `.xlsx` is generated from this on demand for download and parsed back into it on upload; it is never itself written to this archive |
| `data_cache/manifest.csv` | ★ The manifest table — the chart URL table and the canonical index of every chart in the workfile, one row per chart URL, keyed permanently by `hex_id`. Column schema below |
| `data_cache/{hex_id}.json` | One file per fetched chart — serialised data shape, named by the owning manifest row's `hex_id` |
| `template/MyWorkfile.pptx` | Reference copy of the cleaned template — validation only. Never run from. Compared against the live sibling `.pptx` (below) to warn on structural drift |
| `workfile_info.json` | Stored uncompressed (`ZIP_STORED`) — cheap to read alone, before the rest of the archive loads. Contains `workfile_name`, `last_saved_by`, `last_saved_at`, `chartgen_version`, `locked_by` (advisory concurrency), `locked_at` (see Decision 4) |

**Population table shared spine.** Every population-level table — `nhs_organisations`, any `submissions_{year}_{project_id}` table, and any future table — shares the same columns:

| Column | Description |
|--------|-------------|
| `unit_id` | Stable internal identifier for the row, within this table |
| `unit_code` | Outward-facing label — display only, never relied on for logic |
| `unit_name` | Display name |
| `soft_parents` | This row's relationship links to other tables. Format: `table_name:id1^id2\|table_name:id3` — `\|` separates entries for different tables, `^` separates multiple ids within the same table. Recorded on the child side only; the table being linked to carries no reverse reference. Deliberately not called "parent": that word implies a strict one-parent-per-row structure, which these relationships don't have — a row can hold zero, one, or several ids in a given table, and can link to any number of different tables at once (e.g. an organisation supporting two ICBs). See Glossary for the naming rationale |
| any `Name()` column | Any number of peer-group columns, e.g. `Region()` — see Additional peer group columns, Feature List |

A table is free to add `Name()` columns beyond this spine; it may not add any other bespoke column while keeping the identical-headers convention every population table currently follows.

**Running Order column schema** (`running_order.csv`):

| Column | Description |
|--------|-------------|
| `row_id` | Unique integer row identifier (1-based) |
| `enabled` | 1 / 0 — disabled rows are skipped at runtime |
| `scope` | `normal` / `batch_open` / `batch_close` — when the row executes relative to a batch |
| `function` | Function name to call |
| `slide_index` | 0-based slide index (blank for structural functions) |
| `chart_type_ref` | Base Chart function name, e.g. `ranked_column` (blank for non-chart rows) |
| `cache_file` | JSON cache filename supplying data for this chart (blank for non-chart rows) |
| `populations` | Per-row populations string, overriding the project default (blank to use the default) |
| `start_period` | Period_id, TimeSeries rows only — inclusive range start (blank = from the first period). See Decision 12 |
| `end_period` | Period_id, TimeSeries rows only — inclusive range end (blank = to the last period). See Decision 12 |
| `metric_periods` | `^`-delimited period_id(s), TimeSeries rows only — converts the row to a NumericSeries snapshot before rendering (blank = no conversion). See Decision 12 |
| `image_path` | Source image path for `insert_picture`; may contain `[code]`/`[id]` tokens |
| `excel_path` | Workbook path for `open_excel` / `insert_from_excel` / `close_excel` |
| `export_range` | Excel named range captured as an image by `insert_from_excel` |
| `driver_range` | Excel named range receiving the current `unit_id` |
| `left_emu` | Left position in EMU — populated from template |
| `top_emu` | Top position in EMU — populated from template |
| `width_emu` | Width in EMU — populated from template |
| `height_emu` | Height in EMU — populated from template |
| `notes` | Free text; user reference only, ignored at runtime |

**Manifest table column schema** (`data_cache/manifest.csv`):

| Column | Description |
|--------|-------------|
| `chart_ref` | Display index (`Chart_0001` style) — renumbered across non-deleted rows on every add, delete, or reimport; blank on deleted rows |
| `hex_id` | 5-digit uppercase hexadecimal internal identity — stable for the row's lifetime, never reused, never renumbered; names the row's cache file |
| `url` | The toolkit URL |
| `chart_title` | Chart title, taken from the fetched data shape |
| `database` | Source database — `nhs` or `indicators`, resolved at URL entry by `url_triage.url_to_database` from the URL's path shape |
| `project_id` | Populated at fetch |
| `service_id` | Populated at fetch |
| `year` | Populated at fetch |
| `shape_type` | Canonical data shape name, populated at fetch |
| `source` | `Template` (yellow-box extraction) or `Direct Input` (user-entered via Excel) |
| `deleted` | 1 / 0 — deleted rows stay in the table with `hex_id` reserved and cached data kept, but are hidden from the UI table, excluded from the Excel export, and skipped by fetch. A template re-upload containing a deleted row's URL restores it under the same `hex_id` |
| `added_at` | ISO datetime the row was created |
| `data_updated_at` | ISO datetime the row's data was last fetched |

Fetch-populated cells hold the placeholder `...` until the first fetch.

**Sitting alongside the `.cgw`, not inside it** — these are the only other artefacts a colleague sees on a shared drive:

```
MyWorkfile.pptx
outputs/
  pptx/
  pdf/
```

| Path | Notes |
|---|---|
| `MyWorkfile.pptx` | Cleaned template, user-owned and editable — Decision 2. A separate, real file rather than something buried in the ZIP |
| `outputs/pptx/` | Generated `.pptx` reports, one per batch run output. Recreated fresh wherever the `.cgw` currently lives, including after a Save As — not carried across |
| `outputs/pdf/` | Generated `.pdf` reports. Recreated fresh wherever the `.cgw` currently lives, including after a Save As — not carried across |

**CSV vs JSON.** `running_order.csv`, the population tables under `tables/`, `manifest.csv`: flat, fixed-column, one-row-per-entity — CSV's natural shape, and legible to a non-technical colleague who renames `.cgw` to `.zip`. `data_cache/{hex_id}.json`: nested (serialised dataclasses), never hand-edited. Intentional split, not an inconsistency.

---

## 6. Workfile Domain — In Memory (Runtime)

What exists only while the application is running, for the duration of one open session. Built and discarded; never written to disk except via the explicit Save action (the Workfile domain's on-disk form) or the explicit `save_ppt`/`save_pdf` Running Order functions (their own output, not this domain's own state).

```
Streamlit process (st.session_state)
├── st.session_state["ws"] → WorkfileState
│     workfile_path, workfile_name
│     settings: dict
│     tables: dict — {table_name: list[dict]}
│     table_order: list[str]  — position 0 is the master table
│     running_order_rows: list[dict]
│     manifest_rows: list[dict]
│     cache: dict — {filename: json_string}
│     template_pptx_bytes: bytes | None
│     last_saved_by
│     last_saved_at
│     locked_by
│     locked_at
│     dirty: bool
│     read_only: bool
│
├── st.session_state["token"]
├── st.session_state[...UI flags...]
│
└── Per-batch-run objects
    ├── AssemblyContext
    │     prs: Presentation
    │     output_path: str
    │     template_path: str
    │     log: list[dict]
    │     autotable_stats: dict
    │     report_context: ReportContext
    │     full_unit_set: dict — {table_name: list[dict]} for the current reporting unit
    │     default_populations: str
    │     excel_workbooks: dict
    │
    ├── ReportContext
    │     unit_id: str
    │     unit_code: str
    │     unit_name: str
    │
    └── list[NumericSeries | NumericCompositional | CategoricalCompositional]
          population_label: str  — set per layer by build_population_layers
          population_table: str  — which population table this data's units belong to, set at fetch
```

| Item | Notes |
|---|---|
| `st.session_state["ws"]` → `WorkfileState` | ★ The working copy of the open `.cgw` |
| `WorkfileState.settings: dict` | Mirrors `workfile_config/settings.csv` |
| `WorkfileState.tables: dict` | Mirrors `workfile_config/tables/*.csv` — every population-level table |
| `WorkfileState.table_order: list[str]` | Mirrors the `table_order` setting. `master_table_rows()` reads `table_order[0]` — the only definition of "master" anywhere in the system |
| `WorkfileState.running_order_rows: list[dict]` | ★ Sole live copy — see Section 5 note |
| `WorkfileState.manifest_rows: list[dict]` | Mirrors `data_cache/manifest.csv` — the manifest table |
| `WorkfileState.cache: dict` — `{filename: json_string}` | Mirrors `data_cache/{hex_id}.json` files |
| `WorkfileState.dirty: bool` | Not persisted — session-only flag |
| `WorkfileState.read_only: bool` | Not persisted — session-only. True only for a session opened via Open Read-Only; such a session never writes or clears the lock. |
| `st.session_state["token"]` | API session token (Decision 7) — never the password |
| `st.session_state[...UI flags...]` | `show_new_form`, `ro_selected_idx`, etc. — disposable, no domain meaning beyond this widget render |
| Per-batch-run objects | Live only for the duration of one Run Selected / Run Batch / Run All call — constructed fresh, discarded after |
| `AssemblyContext` | One per **batch** (persists across reports within it) |
| `AssemblyContext.report_context: ReportContext` | Rebuilt per report, see below |
| `AssemblyContext.full_unit_set: dict` | Rebuilt per report, alongside `report_context` — the current reporting unit's own row plus every row related to it one hop out (via `soft_parents`, both directions), keyed by table name. `insert_chart` looks up the data shape's own `population_table` in this dict to find the correct rows/selected-unit(s) for that specific chart, rather than assuming the master table applies to every chart |
| `AssemblyContext.excel_workbooks: dict` | Added dynamically by `open_excel`, Insert From Excel |
| `ReportContext` | One per **report** (rebuilt fresh per unit, from the per-report settings dict, never from `load_settings()` — batch overrides apply correctly). Carries no organisation identity — organisation, if the reporting unit's table has one, is reached via `full_unit_set`, not a field on `ReportContext` itself |
| `list[data shape]` | One list per `insert_chart` call — built fresh by `build_population_layers()` each time; each entry is a filtered copy of the chart's data shape, stats recalculated |
| `population_label: str` | Field on the data shape itself — e.g. `"All"`, `"Selected"`, or a resolved peer-group value |
| `population_table: str` | Field on the data shape itself, set once at fetch (`fetch.py`) — the name of the population table this chart's units belong to, not derived at read time |

Only `WorkfileState` (Decision 1) holds real state. `AssemblyContext`, `ReportContext`, and population-filtered data shape lists are just rebuilt from it on every run, the way any app rebuilds working objects from its underlying data rather than treating them as sources of truth in their own right. If the Streamlit process dies mid-session, everything here is gone except whatever was already saved.

---

## 7. Design Decisions

### Decision 1 — Workfile File Format (`.cgw`)

ChartGen workfiles are saved as a single `.cgw` file — internally a ZIP archive, the same pattern as `.pptx`, `.docx`, and `.xlsx`. The extension signals to Windows that the file belongs to ChartGen. Full internal structure in Section 5.

The Running Order's canonical store is `running_order.csv` inside the `.cgw` — a flat table, not xlsx. The `.xlsx` is a human-facing export/import format only, never itself stored in the workfile.

All working state during a session lives in the in-memory `WorkfileState` object, not on disk (Section 6) — the same convention as Word, Excel, and PowerPoint. `WorkfileState` is owned and managed exclusively by `workfile_file`; no other package touches the ZIP directly.

**Memory footprint.** All workfiles are structured text (CSV, JSON). Chart data — the largest component — runs to approximately 50–100KB per chart. A large workfile with 200 charts holds under 20MB in memory. Not a concern.

**Rationale.** Same working pattern as common MS Office applications.

### Decision 2 — Cleaned Template Asset

The cleaned template (yellow textboxes stripped) is saved as a named `.pptx` file alongside the workfile, with an identical base name (see Section 5 for the layout). The user owns `MyWorkfile.pptx` — they may open it directly in PowerPoint and edit it. ChartGen always runs from this file.

**Two edit tiers.** *Cosmetic edits* (text, colours, fonts, non-placeholder shapes) — the user edits `MyWorkfile.pptx` directly; ChartGen picks it up silently on the next run, no reprocessing needed. *Structural edits* (slides added/removed, placeholders moved/renamed, new yellow boxes) — the user edits the original marked-up template and re-uploads it; this overwrites `MyWorkfile.pptx` and the reference copy inside the `.cgw`, and regenerates the Running Order.

Outputs are written to `outputs/pptx/` and `outputs/pdf/` alongside the workfile, created automatically on first run.

### Decision 3 — Template Validation

A reference copy of the cleaned template is stored inside the `.cgw` (`template/MyWorkfile.pptx`) at the point of processing. This copy is never run from — it exists solely for validation.

**Validation at run time.** ChartGen extracts the ordered list of slide layout names from both the reference copy (inside `.cgw`) and the live asset (`MyWorkfile.pptx` alongside the workfile). Matching lists — proceed silently. Differing lists — surface a specific, actionable warning naming exactly which slides changed and how. The warning is soft; the user can proceed or reprocess.

**Why layout names, not slide count.** Layout name comparison catches slides added, removed, reordered, or with a swapped layout — all of which affect placeholder positions and indices in the Running Order. It does not warn for cosmetic edits within a slide, which is correct — those edits are intentional and safe.

### Decision 4 — `workfile_info.json` (Metadata and Concurrency)

Sits in the root of the `.cgw`, stored uncompressed (`ZIP_STORED`), so it can be read from the ZIP by name, without loading the full archive, cheaply at Open time, before `WorkfileState` is fully loaded.

Serves two purposes: session metadata (audit trail, sidebar display) and concurrency signalling (soft lock). Contents shown in Section 5.

`locked_by`/`locked_at` are written when a user opens the workfile and cleared when they close it. When `locked_by` is present, the user opening the file sees an advisory decision step naming the holder and the time — they can choose to open normally or open Read-Only. A hard block is not appropriate, since the lock may be stale (crash, force-quit) with no automatic way to distinguish a live lock from an orphaned one.

**Why inside the ZIP, not a sibling file.** A sibling lock file would be visible on SharePoint as a separate item, and a source of confusion for colleagues. The lock fields inside `workfile_info.json` are invisible to anyone not opening the workfile in ChartGen — the right audience for the warning.

Lock behaviour for each sidebar operation, and for a crash, is in Decision 6.

### Decision 5 — Concurrency

Managed entirely via the lock fields in Decision 4 — no external lock file.

The model is advisory: opening a workfile always shows a decision step (Decision 6) naming the lock state, if any, and offering Open or Open Read-Only. Open Read-Only proceeds without claiming the lock. Last-write-wins applies if two users choose Open and both save — acceptable for a small team with normal verbal coordination. A hard concurrency lock is explicitly out of scope. Per-operation lock behaviour is in Decision 6.

### Decision 6 — File Operations and UI

File operations live in the Streamlit sidebar, tab-agnostic. The main tab interface is only active when a workfile is open; with none loaded, tabs are present but empty.

| Operation | Behaviour |
|---|---|
| **New Workfile** | Collects a short description ("what is this for") and a save location/name via a single native Save dialog, then creates a blank `.cgw` — no project, no population tables. See Decision 9. |
| **Open Workfile** | File picker for `.cgw`. Always leads to a decision step naming the lock state before the workfile loads, offering Open or Open Read-Only. Open writes the lock; Open Read-Only does not. |
| **Save** | Serialise `WorkfileState` to ZIP, update `workfile_info.json`. No confirmation dialog. Disabled in a Read-Only session. |
| **Save As** | Single native Save dialog for name and location together; the OS dialog itself confirms overwrite, so this has no separate app-level overwrite step. Copies the cleaned template alongside the new `.cgw` under the matching name; releases the lock on the old file, writes a new one. Outputs are not carried across. In a Read-Only session, the target folder must differ from the original workfile's; on success the session becomes normal, and the old file's lock is released only if this session had held it. |
| **Save and Close** | Save, then clear `locked_by`+`locked_at`, return to no-workfile-loaded state. Disabled in a Read-Only session. |
| **Close Without Saving** | Confirms if dirty. Clears the lock; ZIP otherwise untouched. Skips the confirmation in a Read-Only session — closes immediately regardless of unsaved edits. |

Buttons are active/inactive based on the state of the software.

**Crash.** Lock fields remain as last written. The next user opening the workfile sees the stale lock as the same decision step described above.

**Read-Only sessions.** Offered on every Open regardless of lock state. Enforcement is shallow: Save is disabled; every other action behaves as normal, so unsaved edits are lost unless rescued via Save As. A Read-Only session never writes the lock, and therefore never clears one on close.

### Decision 7 — Credentials Location and Validation Timing

Only the username is stored, in `core/session_shell/auth/credentials.csv` — rewritten on every successful sign-in, saving the user from re-entering it next time. The password and session token are never persisted to disk; the token lives only in `st.session_state["token"]` for the session's duration.

Validation is a page-level gate (`core.ui.auth.login_form.render_login_gate`, Functional Spec Section 3) rendered before anything else — sidebar, workfile creation/opening, every tab — regardless of launch route (direct, or via a `.cgw` file association). This replaced an on-demand model (a credentials box in a since-removed Config tab) under which a workfile could be opened, and its advisory lock claimed (Decision 5), with a blank username — `classify_lock_state` reads a blank `locked_by` as unlocked, so the lock was silently non-functional for anyone who skipped validation. The gate closes that gap as a side effect: `username` is now always populated before any workfile action is possible.

Save attribution (`last_saved_by`) reads `st.session_state["username"]` directly — now always populated by the time any workfile action is possible, so the save history is never blank.

This is per-machine, per-user data, not workfile data, so it lives in `session_shell/auth/` rather than the workfile or static config.

### Decision 8 — SharePoint Compatibility

ChartGen is designed for a SharePoint-hosted team environment accessed via OneDrive sync.

Charts render entirely in memory as bytes; the only disk writes during a batch run are the final `save_ppt`/`save_pdf` calls, one per report. The `.cgw` is read once at the start of a run and not written again until Save. This avoids the small, rapid file writes that trigger OneDrive sync issues, and leaves the sync client nothing to lock mid-run.

Files accessed via OneDrive sync appear as ordinary local filesystem paths to Python — `zipfile`, `open()`, `shutil` all work unmodified. This avoids the filesystem-API incompatibilities that affect COM/VBA approaches against SharePoint's virtual file system.

### Decision 9 — New Workfile / Population Tables Divorce

Creating a workfile and populating it with a project's data are two unrelated processes, not one flow with two halves.

`create_new_workfile` (`workfile/setup/`) makes a blank `.cgw` — file, description, settings scaffold — with no knowledge that population tables exist, ever will exist, or what an NHS toolkit project even is. `add_project_tables` / `ensure_population_tables` (`acquisition/toolkit_nhs/population_tables.py`) fetch and build a project's population tables against any `WorkfileState`, new or long-established, with no knowledge of whether the workfile it's given was just created.

**Trigger.** Nothing user-facing decides when a project's tables get built. `fetch.py` identifies a chart's own `year`/`project_id` (from its URL and the toolkit API) during that chart's own pull, and calls `ensure_population_tables` at that point: if that project/year's submissions table already exists, nothing happens; if it doesn't, it's built there and then, before the chart's own data is fetched. The first chart pulled for a given project/year is what builds its tables — every subsequent chart for the same combination is a no-op check.

**Merge, not overwrite.** `nhs_organisations` is shared across every project in a workfile. Adding a further project's tables appends organisations not already present (by `unit_id`) rather than rebuilding the table from scratch; existing rows are untouched. This relies on `Region()` (and any future peer-group column) being a value handed to us per-organisation by the API, not something computed from the full table — if that stopped being true, this merge would need revisiting.

**Why acquisition, not workfile.setup.** Building population tables is the same kind of concern as the rest of `acquisition/toolkit_nhs/` — pulling and normalising NHS toolkit data — not a workfile-creation concern. It also has to live there for `fetch.py` to call it directly: acquisition code must never depend on `workfile.setup` (Section 2's one-way dependency rule), and this logic used to sit in `workfile.setup`, which is exactly why it had to move.

### Decision 10 — Second Toolkit (Indicators) and Dual Population-Table Maintenance Models

A second data source — the Indicators toolkit, timeseries data — was added this session, structured as its own package (`acquisition/toolkit_indicators/`) mirroring `toolkit_nhs/`'s shape, rather than as a variant or extension of the NHS package.

**URL triage.** Every URL entering the chart URL table is classified `"nhs"` or `"indicators"` at manifest-row creation, by path shape alone (`url_triage.py`) — `/outputs/{id}` vs `/project/{id}/toolkit`. Both toolkits share the same front-end domain; path is the only reliable signal. Triage happens once, at entry, not at every fetch — the manifest row's `database` column is the single source of truth from that point on.

**Two packages, not one.** `toolkit_indicators/` has its own `api_client.py` (a different API host, `icsapi.nhsbenchmarking.nhs.uk`), `url_parser.py` (a completely different URL shape — a path-embedded project id plus a drill-down breadcrumb of up to four query params, only the deepest of which identifies the actual report tier), `transformers.py`, `table_naming.py`, `population_tables.py`, and `fetch.py`. `fetch_dispatch.py` sits outside both, combining each toolkit's own `fetch_all` into the single Fetch action the Imports tab calls — the same reason `url_triage.py` sits outside both: something has to know about both without either toolkit package depending on the other (Section 2's one-way dependency rule applies between sibling packages too, not just up/down a hierarchy).

**Shared token.** Confirmed: one credential set/token authorises both APIs. `toolkit_indicators` does not duplicate `get_token` — it imports it directly from `toolkit_nhs.api_client`.

**`cache_writer.py` moved to `shared/infrastructure/`.** Audited and confirmed to have no NHS-specific logic — it only serialises whatever dataclass shape it's given. Duplicating it per toolkit package would have meant two copies of genuinely identical code; moved once, both toolkits import from the same place.

**Two different population-table trigger models, deliberately.** `toolkit_nhs/population_tables.py`'s `ensure_population_tables` builds a project's tables once, the first time that project/year is seen, then no-ops forever after — correct for the NHS side, where one chart fetch reveals one snapshot and a stable population. Neither holds for Indicators: a single report fetch already returns a project's entire period history in one response, so even the *first* build has to union submissions across every period in that one call; and submissions genuinely drop in and out of the Indicators population over time, confirmed, so even an established table has to reconcile on every subsequent fetch, not just the first. `toolkit_indicators/population_tables.py`'s `merge_timeseries_population` therefore merges on every call — same append-by-`unit_id`, no-overwrite rule `nhs_organisations` already uses for cross-project merging, just run every time here rather than only once.

**Organisation identity resolution.** The two databases' organisation id spaces were confirmed not to match — the earlier same-id assumption was wrong. `soft_parents` now links each submission to `nhs_organisations:{unit_id}` via a live mapping (ics `organisationId` → nhs `unit_id`) taken from the same `/projects/{id}/submissions` response used for visible dates (`api_client.get_project_submissions_data`) — resolved fresh on every fetch, per project, rather than from a static file. A submission whose organisation has no entry in that mapping is still added, with no `soft_parents` link and `Region()` left blank; `fetch.py` surfaces one warning per fetch run rather than per submission. A newly-resolved organisation not yet in `nhs_organisations` is enriched via `toolkit_nhs.api_client.get_organisations` (current calendar year, since Indicators data has no year of its own) for its canonical name and `Region()`, falling back to the Indicators response's own `organisationName`/`organisationCode` with a blank `Region()` only if that organisation isn't present in that year's NHS list. Submission `unit_name` is sourced from the same project-level response's real `submissionName`; `unit_code` remains `anonSubmissionCode` — previously both fields held the same anonymised value.

**Naming.** `submissions_timeseries_{project_id}` — no year component, unlike the NHS side's `submissions_{year}_{project_id}`. The Indicators toolkit has periods, not years, and a single fetch response already spans every period at once; the table was never partitioned by year to begin with.

### Decision 11 — Charts Sheet Round-Trip Field List and Row Identity

The Charts sheet's two-way sync with the Running Order (Functional Spec Section 9.3) is built over a single maintained field list, `CHART_SANDBOX_FIELDS` (`running_order/schema.py`) — `chart_type_ref`, `cache_file`, `populations`, `start_period`, `end_period`, `metric_periods`, `width_emu`, `height_emu`. The Charts sheet's load and save logic both iterate this list rather than naming each field individually; extending the sync to a future field (e.g. a shape-specific analytical field, per the Primer's normalisation-at-the-boundary principle) is a one-line addition to this list, not a rework of the sync mechanism.

**Row identity is by `row_id`, not list position.** A row selected in the Charts sheet is tracked by its `row_id` across reruns, since an Overwrite leaves `row_id` unchanged while an Insert (`row_ops.insert_new_row`) renumbers every `row_id` after the insertion point (`row_ops.renumber_row_ids`). Rather than resolving a stale index after every save, the Charts sheet clears its row-referencing state (bound row, target row) immediately after any save and requires a fresh selection — simpler and safer than trying to track a moving position.

**`row_ops.py` is deliberately separate from `generation.py` and `dialog_support.py`.** `generation.py` builds rows from a template read result; `dialog_support.py` governs the Running Order tab's own row-edit dialog validity rules. `row_ops.py` holds only generic list operations (insert relative to a row, overwrite fields, renumber) with no knowledge of charts, shapes, or the Charts sheet — the Charts sheet is simply its first caller, not a reason to couple the module to it.

**Page size is captured once, at template processing, the same trigger point as the cleaned template asset (Decision 2).** `template_page_width_emu`/`template_page_height_emu` are read from the `.pptx` at that point and written into `settings.csv` — workfile-level metadata, not a chart-specific fact. `core/shared/infrastructure/page_sizing.py` converts between this page size and a percent-of-shorter-dimension unit; this conversion is a Charts-sheet-authoring concern only; batch execution (`assembly_engine.py`) continues to read and write `width_emu`/`height_emu` directly and is unaffected.

### Decision 12 — Period Range, Convert Periods to Metrics, and Their Excel Dropdowns

Two TimeSeries-only Running Order columns, both added this session: `start_period`/`end_period` (a continuous range trim) and `metric_periods` (one or more discrete periods, converting the row to a NumericSeries snapshot — `shape_transforms.time_series_to_numeric_series`). Both are applied in `assembly_engine.insert_chart` ahead of `build_population_layers` — a normalisation step at the boundary (Primer, Section 4), so the charting side never needs to know either was involved. The range trim runs first; a `metric_periods` id that the range trim has already cut out then correctly surfaces as an unresolvable id, rather than silently succeeding against the untrimmed shape.

**Why a separate cross-shape module.** `shape_transforms.py` sits outside `shapes/` for the same reason `url_triage.py` sits outside both toolkit packages (Decision 10): converting between two shapes needs to know about both without either shape module depending on the other.

**Chart-type validity follows the conversion.** `get_valid_chart_refs_for_cache_file` takes a `converts_to_metrics` flag — true whenever a row's `metric_periods` is set — and substitutes NumericSeries's valid chart types for TimeSeries's, for that row only. This is what keeps the Charts sheet, the Running Order edit dialog, and the xlsx's own per-row `chart_type_ref` dropdown all offering the right options as `metric_periods` is added or removed.

**Excel dropdowns via a hidden list sheet, not an inline formula.** Excel's inline list validation (used for `function`/`chart_type_ref`/etc.) is capped at 255 characters — fine for a handful of options, not for a chart's full period history. A hidden sheet (`_period_lists`) holds each distinct cache_file's period options in its own column (consecutive — column 1 for the first cache_file encountered, and so on); `start_period`, `end_period`, and `metric_periods` all validate against the same column for a given cache_file, one shared `DataValidation` object per cache_file rather than a fresh list per row. The dropdown itself is always single-value (Excel has no multi-select list validation) — `metric_periods` is the one column where more than one may be wanted, so a cell already holding a `^`-delimited value (Charts sheet multi-select, or typed by hand) isn't blocked by the dropdown being there; it just makes adding or replacing one value easy without knowing a period_id.

**Display format.** Cells show `period_label(period_id)` rather than a bare id (meaningless to the user) or a bare label (Excel risks reinterpreting e.g. "Jan 24" as a date). The parenthesised id is what `xlsx_reader.py` extracts back into canonical storage on import; a cell that doesn't match the pattern (blank, or free text typed over the dropdown) resolves to nothing, the same "unresolvable → nothing" rule as an unresolvable population token.

### Decision 13 — Yellow Box Resolution Without Placeholder Containment

The original yellow-box convention required a textbox to sit fully inside a placeholder. Placeholders exist only in PowerPoint's Slide Master/Layout system — a template designer cannot add one to an existing slide in normal edit view, only build or edit a layout in Slide Master view. This makes the placeholder-only route unusable for content added after a template's placeholders are already fixed, which is expected to be the common case for ad hoc additions, not an edge case.

`template_reader.read_template` resolves each detected yellow box against the slide's placeholders into one of three outcomes, checked in this order:

1. **Fully contained** — matched to the placeholder; the placeholder's own position/size are used, unchanged from the original convention. The placeholder is removed from the cleaned template alongside the box.
2. **No overlap with any placeholder** — free-floating. The box's own position/size are used directly, and it is carried through as its own `PlaceholderInfo` entry, named after its own PowerPoint shape name (there being no placeholder name to use). Only the box itself is removed from the cleaned template.
3. **Partial overlap with a placeholder, short of full containment** — ambiguous. Left entirely alone: not classified, not added to the Running Order, not removed from the cleaned template. A warning is raised.

**Why partial overlap is rejected rather than resolved.** A box straddling a placeholder boundary could reasonably be read as intending either the placeholder's bounds or its own — there's no reliable signal for which, so the designer is asked to resolve the ambiguity themselves (move the box fully in, or fully out) rather than the system guessing.

**Precision trade-off, accepted.** A contained box gets pixel-perfect position/size for free, from the placeholder. A free-floating box is only as precise as the designer draws it — the accepted cost of supporting ad hoc content addition without Slide Master skills. The Running Order's `left_emu`/`top_emu`/`width_emu`/`height_emu` columns, and the Charts sheet's percent-of-page fields, remain the route to pixel-perfect placement for a free-floating box, at the cost of the designer doing that adjustment manually.

**Unrecognised content is now warned, not silent.** A yellow box whose text matches none of the three content types (chart URL, picture path, Excel path+ranges) is still stripped from the cleaned template, but now raises a warning naming the slide and a text preview, rather than being silently dropped.

**Warning summary.** If a template read produces any warning at all — unrecognised content, ambiguous overlap, or multiple boxes matched to one placeholder — a single summary line is prepended to the warnings list, so a partial failure is visible without reading every individual entry.

### Decision 14 — Theme-Referenced Fill Colour Resolution

PowerPoint shapes can get their colour two different ways: an explicit literal fill on the shape itself (`<a:solidFill><a:srgbClr>`), or a "Shape Styles" gallery reference that stores no colour at all — only `<p:style><a:fillRef><a:schemeClr val="accentN"/></a:fillRef>`, resolved against the presentation's theme at render time. Yellow-box detection originally only checked for the former; a box styled via the latter route looked yellow on screen but was invisible to detection, since nothing on the shape itself said so.

`_get_shape_fill_rgb` now resolves both, in order: an explicit fill on the shape (literal RGB, or a `schemeClr` theme reference resolved as below); failing that, if the shape defines no fill of its own at all, its style's `fillRef` — again resolved as below. An explicit `<a:noFill/>` on the shape is treated as no fill, full stop — the style reference is not consulted in that case.

**Resolution walks the full chain, not just a name lookup.** A `schemeClr` name (e.g. `accent4`) isn't looked up directly against the theme — it first passes through the colour map in effect for that slide (a slide's own `<p:clrMapOvr>` if present, otherwise its slide master's `<p:clrMap>`), which can in principle redirect any of the twelve named slots to a different one. Only the redirected name is then looked up in the theme's `<a:clrScheme>` (via the slide → layout → master → theme relationship chain) for its literal RGB. This handles a non-identity colour map correctly rather than only the common (identity) case. Resolved master-level context (colour map and theme scheme) is cached per master to avoid re-parsing for every shape.

**Simplification, accepted.** The theme's format scheme (`fillStyleLst`) can define a `fillRef` idx as a shaded or gradient variant of the base scheme colour rather than a flat solid. This is not modelled — the base scheme colour is used unmodified. Acceptable for yellow detection, where the hue/saturation/value thresholds already tolerate meaningful colour drift; not intended as a general-purpose theme-colour renderer.

**Containment tolerance.** `_fully_contained` (Decision 13) allows 1mm (36,000 EMU) of drift on each edge, absorbing sub-visible rounding noise — observed in practice as a 1 EMU discrepancy on a shape duplicated via copy/paste — without misclassifying a genuinely-contained box as a partial overlap (Decision 13, scenario 3).
