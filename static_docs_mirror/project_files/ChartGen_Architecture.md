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
| Validate only where designed | Input validation, clamps, and defensive-guard logic are an architectural decision, not a local coding choice -- raised with the architect before adding one, not layered in ad hoc while fixing something else. Data flows are designed to be clean by construction; a validation added defensively elsewhere usually signals a problem upstream that the validation itself doesn't fix, and adds code bulk and its own bug surface rather than removing risk. |

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
    │       │   │   ├── numeric_series/, numeric_compositional/,
    │       │   │   ├── categorical_compositional/, timeseries/
    │       │   │   └── registry.py
    │       │   ├── custom_charts/
    │       │   │   ├── contract.py, gate.py, resolve.py, bundle.py
    │       │   ├── cache_reader.py
    │       │   └── chart_type_map.py
    │       ├── tables/
    │       │   ├── grid_store.py, resolve.py, grid_xlsx.py, insert_table.py
    │       │   ├── base_tables/
    │       │   │   ├── plain_grid.py, table_ledger.py, table_zebra.py,
    │       │   │   ├── table_editorial.py, table_terminal.py, table_cardtile.py,
    │       │   │   ├── table_pill.py, table_freeform.py, table_brutalist.py,
    │       │   │   ├── table_softui.py
    │       │   │   └── registry.py
    │       │   └── custom_tables/
    │       │       ├── contract.py, gate.py, resolve.py, bundle.py
    │       ├── pictures/
    │       │   └── insert_picture.py
    │       ├── excel/
    │       │   └── insert_from_excel.py
    │       └── text/
    │           ├── text_engine.py, stat_tags.py
    │           └── stat_tags_xlsx.py
    ├── shared/
    │   ├── normalisation_containers/
    │   │   ├── shapes/
    │   │   │   ├── common.py, numeric_series.py, numeric_compositional.py,
    │   │   │   └── categorical_compositional.py, timeseries.py, dispatch.py,
    │   │   │   └── reference_ids.py
    │   │   ├── population_layers.py
    │   │   ├── peer_group_tokens.py
    │   │   ├── shape_transforms.py
    │   │   └── cut_resolution.py
    │   └── infrastructure/
    │       ├── constants.py
    │       ├── report_context.py
    │       ├── soft_parents.py
    │       ├── page_sizing.py
    │       ├── cache_writer.py
    │       ├── population_table_xlsx.py
    │       ├── value_formatting.py
    │       ├── period_ids.py
    │       └── id_generation.py
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
            ├── text_tab.py, running_order_tab.py, charts_tab.py,
            └── output_tables_tab.py, outputs_tab.py
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
| `core/output_generation/execution/charts/base_charts/` | 20 built-in Base Charts, one standalone file per base_chart_name, grouped into a folder per canonical data shape. No shared helpers module — each file is fully self-contained, so it can be handed whole to an external AI for editing (Decision 18); dispatch in `registry.py` |
| `core/output_generation/execution/charts/custom_charts/` | Custom Charts — user- or AI-authored Base Charts saved into a workfile. Static validation and compilation (`gate.py`), built-in-then-custom resolution (`resolve.py`), the AI-facing download bundle (`bundle.py`), and the shared contract both enforce and explain (`contract.py`). See Decision 18 |
| `core/output_generation/execution/charts/` (remainder) | Cache reading; `chart_type_map.py` |
| `core/output_generation/execution/tables/grid_store.py` | Output Table grid storage shape and mechanics — `col_key`/`new_grid`/`grid_dimensions`/`get_column_widths`/`get_row_heights`/`get_content_grid`/`validate_grid`/`resize_grid`, plus `next_table_id` (via `id_generation`). Mirrors the population tables' own "no fixed schema, each written from its own rows' keys" convention |
| `core/output_generation/execution/tables/resolve.py` | `resolve_output_table` — resolves an Output Table's grid into plain values ready for a Base Table renderer: parsed column widths/row heights, and a content grid with every Stat Tag resolved via `text_engine.build_stat_tag_tokens` (the same token map `update_text` uses, not duplicated) |
| `core/output_generation/execution/tables/grid_xlsx.py` | `write_output_table_xlsx`/`read_output_table_xlsx` — full-replace Excel round-trip for a single Output Table's grid, mirroring its own spreadsheet shape directly rather than a flat table; content cells carry a Stat Tag id dropdown via a hidden list sheet (Decision 12's pattern), free text still accepted alongside it |
| `core/output_generation/execution/tables/insert_table.py` | `insert_table` Running Order function — the Output Table equivalent of `insert_chart`, kept in its own module for the same reason `update_text` was promoted out of `assembly_engine` (Decision 20). Resolves `table_type_ref` built-in-then-custom via `custom_tables.resolve.get_table_callable`, the same pattern `insert_chart` uses for Custom Charts |
| `core/output_generation/execution/tables/base_tables/` | Ten built-in Base Tables, one standalone file per `table_type_ref`, no shared helpers module — the same self-containment convention as `base_charts/` (Decision 18); dispatch in `registry.py`. See Decision 24 |
| `core/output_generation/execution/tables/custom_tables/` | Custom Tables — user- or AI-authored Base Tables saved into a workfile. Mirrors `charts/custom_charts/` field for field (`contract.py`, `gate.py`, `resolve.py`, `bundle.py`), for the table domain rather than the chart domain — kept as its own copy, not shared, since the two rendering domains are deliberately independent. See Decision 24 |
| `core/output_generation/execution/pictures/insert_picture.py` | `insert_picture` Running Order function |
| `core/output_generation/execution/excel/insert_from_excel.py` | Excel COM capture (`open_excel` / `insert_from_excel` / `close_excel`) |
| `core/output_generation/execution/text/text_engine.py` | `update_text` Running Order function — per-unit tags and Stat Tags alike, ordinary text frames and PowerPoint table cells alike. Promoted out of `assembly_engine` to its own module; the resolution logic for a Stat Tag itself lives in `stat_tags.py`, this module only builds the combined token dict and walks the presentation. See Decision 20 |
| `core/output_generation/execution/text/stat_tags.py` | Stat Tags: `next_stat_tag` (base-36 counter, via shared `id_generation`), `layer_display_label`, `resolve_stat_cut`/`resolve_stat_tag_value` — resolves one `text_stats.csv` row to a value for the current reporting unit, via `cut_resolution.prepare_chart_cut`. Also exposes `build_stat_tag_tokens` (in `text_engine.py`, public — see below), reused by Output Tables' own cell resolution. See Decision 19 |
| `core/output_generation/execution/text/stat_tags_xlsx.py` | Excel download/upload round-trip for `text_stats.csv` — full-replace on upload, the same pattern as the Running Order's own xlsx pair, not the manifest table's identity-merge one. See Decision 19 |
| `core/output_generation/static_config/chart_type_map.csv` | Data shape → valid chart type refs (developer-owned, read-only) |
| `core/shared/normalisation_containers/` | NumericSeries / NumericCompositional / CategoricalCompositional / TimeSeries, split into one module per shape under `shapes/`, each owning its shape's canonical Metric-Series stats computation and summary statistics (plus `common.py` for the shared `Unit`/`ShapeStats` base, `dispatch.py` for `filter_shape`/`summary_stats`/`summary_stats_by_layer`/`shape_units`/`units_by_layer`/`apply_period_range`, and `reference_ids.py` for converting a shape's summary stats into short id-tagged rows for display — see Decision 15); `build_population_layers`; the shared peer-group token rule; `shape_transforms.py` for cross-shape conversions (see Decision 12); `cut_resolution.py` composing the shared middle of "resolve a chart's own cut" — period trim, metric-periods conversion, population-table/target-rows/selected-ids resolution — used by `insert_chart`, the Charts sheet, and Stat Tags alike (see Decision 22) |
| `core/shared/infrastructure/constants.py` | `coerce_row` / `FIELD_TYPES` — generic CSV/WorkfileState field-type coercion, used by `api_client`, `running_order`, and `workfile_file`; also `SPINE_COLUMN_ORDER`, the population-table spine's display/authoring column order, shared between the UI and the Excel round-trip below |
| `core/shared/infrastructure/report_context.py` | `ReportContext` + `build_report_context()` |
| `core/shared/infrastructure/soft_parents.py` | `format_soft_parents` / `parse_soft_parents` / `resolve_related_rows` / `resolve_referencing_rows` / `resolve_all_related_rows` / `resolve_full_unit_set` — the `soft_parents` relationship format and its one-hop resolution, both directions. Generic across any population table, not NHS-specific |
| `core/shared/infrastructure/page_sizing.py` | `percent_to_emu` / `emu_to_percent` / `get_page_size_emu` / `has_known_template_page_size` — conversion between EMU and a percent-of-shorter-page-dimension unit, and resolution of which page size to convert against (the real captured template size once known, a manual standard-size fallback otherwise). Used by the Charts sheet only; has no bearing on batch execution, which continues to work in raw EMU throughout |
| `core/shared/infrastructure/cache_writer.py` | `save_chart` — serialises any canonical data shape into `WorkfileState.cache`. Moved here from `acquisition/toolkit_nhs/` this session: audited as having no NHS-specific logic at all, so it's shared by both toolkit packages rather than duplicated. See Decision 10 |
| `core/shared/infrastructure/population_table_xlsx.py` | Excel export/import round-trip for any population-level table — the workfile-state equivalent of the manifest table's own xlsx pair (`acquisition/manifest_table/`). Generic across any table's own columns; identity is `unit_id`, not a system-generated key |
| `core/shared/infrastructure/value_formatting.py` | `format_number` / `format_reference_value` — numeric display formatting, moved here from `ui/common/formatting.py` this session so execution-layer code (`update_text`/Stat Tags) can use the same logic without importing from `ui`. `ui/common/formatting.py` re-exports `format_number` for its existing callers. See Decision 22 |
| `core/shared/infrastructure/period_ids.py` | `parse_metric_periods_string` / `build_metric_periods_string` — moved here from `output_generation/definition/running_order/dialog_support.py` this session for the same reason as `value_formatting.py`: `cut_resolution.py` needed them and shared code can't import from `output_generation.definition`. `dialog_support.py` re-exports both. See Decision 22 |
| `core/shared/infrastructure/id_generation.py` | `to_base36`/`next_id` — shared base-36 id-issuing helper. Used by Stat Tags (`settings["next_stat_tag_id"]`) and Output Tables (`settings["next_table_id"]`) alike; each keeps its own counter/settings key under its own name, so the two id spaces never collide or interleave — only the digit-encoding is shared |
| `core/ui/` | Streamlit UI, grouped into `common/` (generic display/picker helpers, per-tab guidance links, layout CSS), `auth/` (the page-level sign-in gate), `workfile/` (sidebar, dialogs, New/Open/Save As forms), and `tabs/` (the eight tab renderers). Business logic delegated to the owning module rather than living here |

---

## 5. Workfile Domain — On Disk (`.cgw`)

A single workfile's complete, portable, shareable state. Internally a ZIP archive — the same pattern as `.pptx`, `.docx`, `.xlsx`.

```
MyWorkfile.cgw  (ZIP)
├── workfile_config/
│   ├── settings.csv
│   ├── tables/
│   │   └── {table_name}.csv
│   ├── running_order.csv
│   ├── text_stats.csv
│   ├── custom_charts/
│   │   ├── custom_charts.csv
│   │   └── {shape_type}/
│   │       └── {base_chart_name}.py
│   ├── output_tables/
│   │   ├── output_tables.csv
│   │   └── {table_id}.csv
│   └── custom_tables/
│       ├── custom_tables.csv
│       └── {table_type_ref}.py
├── data_cache/
│   ├── manifest.csv
│   └── {hex_id}.json
├── template/
│   └── MyWorkfile.pptx
└── workfile_info.json
```

| Path | Notes |
|---|---|
| `workfile_config/settings.csv` | key,value — paths, `table_order`, `batch_cursor`, workfile description, `template_page_width_emu`/`template_page_height_emu` (captured once at template processing — see Decision 11), `charts_sheet_state` (a JSON blob of the Charts sheet sandbox's own current control values — see Decision 21), `next_stat_tag_id` (Stat Tags counter — see Decision 19), etc. Deliberately holds no project identity (no year, project_id, project_name) — a workfile can span more than one project, so none of those are workfile-level facts any more; see the shared spine below for where project/year identity actually lives |
| `workfile_config/tables/{table_name}.csv` | ★ One file per population-level table (e.g. `nhs_organisations.csv`, `submissions_2026_123.csv`) — any number of them, added and removed freely. No single fixed column schema at this layer; each is written using its own rows' keys. `table_order` (in `settings.csv`, `\|`-delimited) is the only record of display order — whichever table name is listed first is the master table, driving the reporting unit picker and the batch loop. No separate "master" flag exists; position is the only source of truth |
| `workfile_config/running_order.csv` | ★ Canonical Running Order store — flat table, not `.xlsx`. The `.xlsx` is generated from this on demand for download and parsed back into it on upload; it is never itself written to this archive |
| `workfile_config/text_stats.csv` | ★ Stat Tags (Decision 19) — one row per tag, keyed by its own `tag`. Column schema below |
| `workfile_config/custom_charts/` | Custom Charts saved into this workfile (Decision 18) — `custom_charts.csv` is the index (`base_chart_name`, `shape_type`, `added_at`, `notes`); one `.py` per row, under a folder named for its `shape_type`, mirroring the built-in Base Charts' own folder-per-shape layout |
| `workfile_config/output_tables/` | Output Tables (Decision 23) — `output_tables.csv` is the index (`table_id`, `table_name`, `rows`, `columns`); one grid CSV per `table_id`, directly under this folder (no per-shape subfolder — an Output Table isn't scoped to any canonical data shape). Column schema below |
| `workfile_config/custom_tables/` | Custom Tables saved into this workfile (Decision 24) — `custom_tables.csv` is the index (`table_type_ref`, `added_at`, `notes`); one `.py` per row, directly under this folder — no per-shape subfolder, mirroring `custom_charts/`'s pattern but flat, since a Base Table isn't scoped to any canonical data shape either |
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
| `base_chart_name` | Base Chart function name, e.g. `ranked_column` (blank for non-chart rows) |
| `cache_file` | JSON cache filename supplying data for this chart (blank for non-chart rows) |
| `table_id` | Output Table id this row renders (blank for non-table rows). See Decision 23 |
| `table_type_ref` | Base Table function name, e.g. `plain_grid` (blank for non-table rows) |
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
| `tweaks` | Free-text string, passed straight through to the Base Chart function's own `tweaks` parameter, uninterpreted by anything in the Running Order/assembly layer (blank = nil-length string). No Base Chart function currently reads it — see Decision 16 |
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

**Stat tags table column schema** (`workfile_config/text_stats.csv`, Decision 19):

| Column | Description |
|--------|-------------|
| `tag` | Base-36 id (`0`–`9` then `a`–`z`), never reused — the literal `[tag]` template text. Issued from a persisted counter (`settings["next_stat_tag_id"]`) |
| `hex_id` | Manifest `hex_id` this tag's data comes from — not `chart_ref`, which renumbers |
| `populations` | This tag's own single population token (`All`, `Selected`, `Region()`, `Region(Wales)`, etc.) — independent of any Running Order row |
| `start_period` | Period_id, TimeSeries only |
| `end_period` | Period_id, TimeSeries only |
| `metric_periods` | `^`-delimited period_id(s), TimeSeries only |
| `reference_id` | Which Reference id (Decision 15) to read from the resolved population |
| `description` | Optional free text; user reference only, ignored at resolution |

**Output Tables index column schema** (`workfile_config/output_tables/output_tables.csv`, Decision 23):

| Column | Description |
|--------|-------------|
| `table_id` | Base-36 id (`0`–`9` then `a`–`z`), never reused — also written, cosmetically only, into the grid's own corner cell. Issued from a persisted counter (`settings["next_table_id"]`), via the shared `id_generation` helper |
| `table_name` | User-facing name — user-typed for a manually-created table, auto-generated (`Table_1`, `Table_2`, ...) for a yellow-box one. Never used to match a re-uploaded template's box against an existing table — see Decision 23 |
| `rows` | Content grid row count (N), excluding the header row |
| `columns` | Content grid column count (M), excluding the header column |

**Output Table grid layout** (`workfile_config/output_tables/{table_id}.csv`, Decision 23) — no fixed column schema (same convention as a population table); columns are named `c0`..`cM` generically. An (N+1) × (M+1) grid:

| Cell(s) | Description |
|--------|-------------|
| Row 0, col 0 (corner) | The table's own `table_id`. Display only, never read back for anything |
| Row 0, cols 1..M | Column widths, % of total table width, 2 decimal places |
| Rows 1..N, col 0 | Row heights, % of total table height, 2 decimal places |
| Rows 1..N, cols 1..M | Content cells — constant text, or a Stat Tag id (`[3]`). Chart-component cells (`{3}`) are recognised by the grammar but not resolved or rendered — parked, see Feature List |

**Custom Tables index column schema** (`workfile_config/custom_tables/custom_tables.csv`, Decision 24):

| Column | Description |
|--------|-------------|
| `table_type_ref` | The saved Base Table's own function name — must not collide with a built-in or an existing Custom Table in the same workfile |
| `added_at` | ISO datetime the row was created |
| `notes` | Optional free text; user reference only |

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
│     custom_chart_rows: list[dict]
│     custom_chart_code: dict — {base_chart_name: source_text}
│     text_stats_rows: list[dict]
│     output_table_rows: list[dict]
│     output_tables: dict — {table_id: list[dict]} grid rows
│     custom_table_rows: list[dict]
│     custom_table_code: dict — {table_type_ref: source_text}
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
| `WorkfileState.custom_chart_rows` / `.custom_chart_code` | Mirror `workfile_config/custom_charts/` (index + one `.py` per row) the same way `manifest_rows`/`cache` mirror the manifest/cache pair — see Decision 18 |
| `WorkfileState.text_stats_rows: list[dict]` | Mirrors `workfile_config/text_stats.csv` — Stat Tags. See Decision 19 |
| `WorkfileState.output_table_rows` / `.output_tables` | Mirror `workfile_config/output_tables/` (index + one grid CSV per `table_id`) the same way `tables`/`table_order` mirror the population tables — no fixed grid column schema, see Decision 23 |
| `WorkfileState.custom_table_rows` / `.custom_table_code` | Mirror `workfile_config/custom_tables/` (index + one `.py` per row) the same way `custom_chart_rows`/`custom_chart_code` mirror `custom_charts/` — see Decision 24 |
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

The Charts sheet's two-way sync with the Running Order (Functional Spec Section 9.3) is built over a single maintained field list, `CHART_SANDBOX_FIELDS` (`running_order/schema.py`) — `base_chart_name`, `cache_file`, `populations`, `start_period`, `end_period`, `metric_periods`, `width_emu`, `height_emu`, `tweaks`. The Charts sheet's load and save logic both iterate this list rather than naming each field individually; extending the sync to a future field (e.g. a shape-specific analytical field, per the Primer's normalisation-at-the-boundary principle) is a one-line addition to this list, not a rework of the sync mechanism.

**Row identity is by `row_id`, not list position.** A row selected in the Charts sheet is tracked by its `row_id` across reruns, since an Overwrite leaves `row_id` unchanged while an Insert (`row_ops.insert_new_row`) renumbers every `row_id` after the insertion point (`row_ops.renumber_row_ids`). Rather than resolving a stale index after every save, the Charts sheet clears its row-referencing state (bound row, target row) immediately after any save and requires a fresh selection — simpler and safer than trying to track a moving position.

**`row_ops.py` is deliberately separate from `generation.py` and `dialog_support.py`.** `generation.py` builds rows from a template read result; `dialog_support.py` governs the Running Order tab's own row-edit dialog validity rules. `row_ops.py` holds only generic list operations (insert relative to a row, overwrite fields, renumber) with no knowledge of charts, shapes, or the Charts sheet — the Charts sheet is simply its first caller, not a reason to couple the module to it.

**Page size is captured once, at template processing, the same trigger point as the cleaned template asset (Decision 2).** `template_page_width_emu`/`template_page_height_emu` are read from the `.pptx` at that point and written into `settings.csv` — workfile-level metadata, not a chart-specific fact. `core/shared/infrastructure/page_sizing.py` converts between this page size and a percent-of-shorter-dimension unit; this conversion is a Charts-sheet-authoring concern only; batch execution (`assembly_engine.py`) continues to read and write `width_emu`/`height_emu` directly and is unaffected.

### Decision 12 — Period Range, Convert Periods to Metrics, and Their Excel Dropdowns

Two TimeSeries-only Running Order columns, both added this session: `start_period`/`end_period` (a continuous range trim) and `metric_periods` (one or more discrete periods, converting the row to a NumericSeries snapshot — `shape_transforms.time_series_to_numeric_series`). Both are applied in `assembly_engine.insert_chart` ahead of `build_population_layers` — a normalisation step at the boundary (Primer, Section 4), so the charting side never needs to know either was involved. The range trim runs first; a `metric_periods` id that the range trim has already cut out then correctly surfaces as an unresolvable id, rather than silently succeeding against the untrimmed shape.

**Why a separate cross-shape module.** `shape_transforms.py` sits outside `shapes/` for the same reason `url_triage.py` sits outside both toolkit packages (Decision 10): converting between two shapes needs to know about both without either shape module depending on the other.

**Chart-type validity follows the conversion.** `get_valid_chart_refs_for_cache_file` takes a `converts_to_metrics` flag — true whenever a row's `metric_periods` is set — and substitutes NumericSeries's valid chart types for TimeSeries's, for that row only. This is what keeps the Charts sheet, the Running Order edit dialog, and the xlsx's own per-row `base_chart_name` dropdown all offering the right options as `metric_periods` is added or removed.

**Excel dropdowns via a hidden list sheet, not an inline formula.** Excel's inline list validation (used for `function`/`base_chart_name`/etc.) is capped at 255 characters — fine for a handful of options, not for a chart's full period history. A hidden sheet (`_period_lists`) holds each distinct cache_file's period options in its own column (consecutive — column 1 for the first cache_file encountered, and so on); `start_period`, `end_period`, and `metric_periods` all validate against the same column for a given cache_file, one shared `DataValidation` object per cache_file rather than a fresh list per row. The dropdown itself is always single-value (Excel has no multi-select list validation) — `metric_periods` is the one column where more than one may be wanted, so a cell already holding a `^`-delimited value (Charts sheet multi-select, or typed by hand) isn't blocked by the dropdown being there; it just makes adding or replacing one value easy without knowing a period_id.

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

### Decision 15 — Summary Stats, Reference Ids, and the Always-Present Population Layer

**Rename.** `autotable_stats` (dispatch function) and each shape's own `*_autotable_stats` function were renamed to `summary_stats`/`*_summary_stats`. The old name conflated two things: the stats a shape computes for itself (a property of the data), and Autotables (Feature List: Not built), the future PowerPoint-table-population feature that may eventually consume them. (A `_summary_stats_with_selection` helper and an `AssemblyContext.summary_stats` attribute were added alongside this rename in the same session; both were removed in a later reversal — see Decision 17, which is the current account of how statistics flow through the system.)

**`render_chart`'s return signature is described in Decision 17, not here.** An earlier version of this decision documented `render_chart` returning a 4-tuple `(image_bytes, base_summary_stats, layer_summary_stats, layer_units)`, with Base Chart functions computing and returning their own stats. That mechanism was fully reversed — Base Chart functions now return `image_bytes` only, and statistics are read directly off the data shapes by whichever caller needs them. See Decision 17 for the current, correct account.

**`shape_units`** (`shapes/dispatch.py`) returns the list of Unit-like objects making up a shape's actual population, dispatching per shape type: `shape.units` for NumericSeries; `shape.metrics[0].units` for the other three (every metric-series in one shape instance shares the same population — the existing `ShapeStats` counts already assume this).

**Reference ids** (`shapes/reference_ids.py`) convert a shape's summary stats into short, PowerPoint-tag-safe id-tagged rows (`{"id", "label", "kind", "value"}`), one function per shape type (`numeric_series_reference_rows`, `time_series_reference_rows`, `categorical_reference_rows`, `numeric_compositional_reference_rows`), dispatched via `reference_rows_for_shape_type(shape_type: str, stats: dict)` — keyed by the same shape_type strings already used by `chart_type_map.csv` and `cache_reader.DESERIALISE_MAP`. Scope is per shape type, not global: an id like `Mn` means the same statistic in every NumericSeries table, since every NumericSeries shape shares an identical fixed stat set; compositional shapes carry a running component/category number instead, since component count varies per metric-series but is identical across every metric-series within one shape instance (a valid compositional shape requires this).

Id construction, by shape type:
- **NumericSeries / TimeSeries** — fixed stat-letter prefixes (`C`, `Nd`, `Mn`, `Md`, `Q1`, `Q3`, `Mi`, `Ma`). TimeSeries prefixes a 1-based period number ahead of the stat letter (in `shape.periods` order), since a period axis exists on top of the same fixed stat set.
- **CategoricalCompositional / NumericCompositional** — `C`/`Nr` (categorical) or `T` (numeric) for the fixed part; a 1-based running number identifies each component/category, with a `P`-prefixed twin for its percentage share.
- **All four** — a series letter (`a`, `b`, `c`, ...) is appended last, only when a shape carries more than one metric-series, restarting at `a` for each shape instance (not persistent across shapes). Deliberately no digit-adjacent-to-digit case can arise (e.g. TimeSeries never has components, so a period number is never adjacent to a component number).

Each row also carries a `kind` (`"value"` / `"count"` / `"percent"`) governing display formatting, not calculation: `"value"` respects the shape's own `format_modifier`; `"count"` is always a plain integer; `"percent"` is always shown as a %, independent of `format_modifier` (extending CategoricalCompositional's existing chart-rendering convention — Functional Spec Section 10.2 — to NumericCompositional's component-share figures for the same reason).

**Accepted trade-off.** An id's meaning is not fixed at authoring time — it depends on the shape's current series/component count. A tag typed into a PowerPoint table referencing e.g. `Mn` (no series letter, one series) would mean something different, or break, if a second metric-series were later added to that chart. Accepted deliberately: the alternative (always carrying a series letter, even for a single series) was considered and rejected in favour of shorter ids in the common single-series case.

**Every population-string token now always produces a layer.** `build_population_layers` (`shared/normalisation_containers/population_layers.py`) previously returned `[]` entirely if the first token failed to resolve, and silently skipped (`continue`) any later token that failed to resolve — e.g. no unit currently selected, or the selected unit's own peer-group value blank/unset. This meant a chart's requested populations string (`All^Region()^Selected`) could silently render with only one or two of its three intended layers, with no visible indication anything was missing. `_resolve` (the token-resolution helper) now never returns `None`: an unresolvable token returns an empty id set with its own best-available label (the raw token text, where no resolved value exists) instead. The scope token (first in the string) may now resolve to an empty set; every subsequent token then also resolves empty against it, correctly, rather than the whole layer list disappearing. This holds regardless of whether the currently selected reporting unit has data in this particular chart — resolution depends only on the population table, never on chart data presence.

**Two shape modules needed a matching fix, so an empty layer still displays correctly rather than losing its own structure:**
- **NumericSeries** — `_recalc_numeric_series_stats` previously derived its metric-series count from `units[0].values`, collapsing to `[]` (losing every metric-series name) when the filtered unit list was empty. Now takes an explicit `n_metrics` parameter (`len(shape.metric_names)`), so a zero-unit layer still returns one (all-null) stats entry per metric-series.
- **NumericCompositional** — `numeric_compositional_summary_stats` previously derived its component list from a unit's own `values`, so a zero-unit metric-series produced an empty `Components` dict, losing every component name. Now iterates `metric.component_names` (structural, always present) instead.
- CategoricalCompositional and TimeSeries already handled the zero-unit case correctly (both already iterate structural fields — `shape.metrics`/`category_names` and `shape.metrics`/`shape.periods` respectively — rather than deriving counts from unit data) and needed no change.

**Charts sheet display** (`ui/tabs/charts_tab.py`) shows two labelled sections: "Summary stats" (one collapsed expander per population layer × metric-series, columns Reference/Statistic/Value) and "Units included" (one collapsed expander per population layer, columns ID/Code/Name — "Name" resolved from the population table already loaded for the chart, since a shape's own unit records carry only id and code). Both sections always show one entry per population layer actually passed to the chart, including an empty one — the Units included table shows an explicit "No units in this population layer" note rather than omitting a zero-unit layer entirely. As of Decision 17, both sections are populated by calling `summary_stats_by_layer`/`units_by_layer` directly against the same `population_layers` list passed to `render_chart`, not from anything `render_chart` returns.

### Decision 16 — Chart Tweaks Parameter and Running Order Column

Every Base Chart function's `tweaks` parameter was typed as a list default (`tweaks=[]`) but never read by any function body — a placeholder with no data flowing into it, since the Running Order had no matching column. Retyped to a string default (`tweaks=""`) across all 20 Base Chart functions and `registry.render_chart`, matching a new `tweaks` Running Order column (Section 5) — a free-text string with no interpreted structure, passed straight through, uninterpreted, to whichever Base Chart function renders that row.

**Wiring.** `assembly_engine.insert_chart` reads `row.get("tweaks", "")`, coerced to a stripped string, and passes it through `_render_chart_image` into `render_chart`. A blank column produces a nil-length string, never `None`.

**Charts sheet.** `tweaks` was added to `CHART_SANDBOX_FIELDS` (Decision 11) and given its own text-area control in the Charts sheet, populating from a bound Running Order row's `tweaks` column the same way `populations`/`metric_periods` already do, or typed directly in free-play mode.

**No Base Chart function currently reads `tweaks`.** The parameter and column exist and round-trip correctly end to end; no chart's rendering behaviour currently varies with its value. This is accepted as the starting point for future per-chart tweak behaviour, not a gap to close immediately.

### Decision 17 — Base Chart Statistics Ownership Reversed to the Data Shapes

**The problem.** Every Base Chart function computed `summary_stats(base)` itself and returned it, wrapped with a "Selected value" bolt-on (`_summary_stats_with_selection`), as part of a 2-tuple return (Decision 15's original account). This produced two problems, not one: the return value was computed on every render and stored on `AssemblyContext.summary_stats` per `insert_chart` call, with no consumer anywhere in the codebase ever reading it back (Autotables, the intended future consumer, is not built) — pure waste, every batch run. Worse, the "Selected value" bolt-on was computed two genuinely different ways across chart functions of the *same* shape type: `ranked_column`/`dot_strip` derived it from the scope layer's own units regardless of whether a "Selected" population layer was ever requested, while `box_whisker`/`frequency_histogram`/`violin_plot`/`bead_string_dot_plot` derived it only from an explicitly-resolved `"Selected"` population layer. The same unit, the same data, the same reporting context could show a different "Selected value" purely because of which chart type was picked.

**The principle.** A Base Chart function's job is producing a visual. Statistics and unit lists are a property of the data shape (`core/shared/normalisation_containers/shapes`), not something the charting layer computes, bolts onto, or relays — they should be read from the shapes already in scope wherever they're actually needed, with no intermediate transformation or storage step in between.

**The change.** All 20 Base Chart functions now return `image_bytes` only. `summary_stats(base)` calls, `_summary_stats_with_selection`, and every `sel_val`/`selected_value` line that existed solely to feed a stats return were removed — not left in as dead code. `_summary_stats_with_selection` and `_selected_layer_value` (`base_charts/shared.py`) were deleted outright, having lost every caller. `registry.render_chart` now simply dispatches to the registered function and returns its image; the `summary_stats_by_layer`/`units_by_layer` computation it used to do generically for `layer_summary_stats`/`layer_units` was removed too, since a caller already holds `population_layers` and can call those same shape-dispatch functions directly.

**Consumers updated accordingly.** `AssemblyContext.summary_stats` (Section 6) is removed — `insert_chart` no longer stores anything; if Autotables is ever built, `data_shape`/`population_layers` are already in scope at that point in `insert_chart` for it to read directly. The Charts sheet preview (`ui/tabs/charts_tab.py`) now calls `summary_stats_by_layer`/`units_by_layer` itself, directly against `pop_layers`, right next to where the "Summary stats"/"Units included" display already consumed them — same on-screen output, one fewer hop, no detour through the charting layer.

**Effect on the two-methods inconsistency.** Resolved as a side effect, not by choosing one of the two prior methods — the question of "which Selected-value rule is correct" no longer arises, since no Base Chart function computes or returns a Selected value at all.

### Decision 18 — Base Charts as Standalone Artefacts, and Custom Charts

Base Charts are now treated the way an Excel `.crtx` chart-type template is treated — a rendering artefact, not application logic. Each of the 20 built-ins was rewritten into its own standalone file (`base_charts/{shape}/{base_chart_name}.py`), carrying its own copy of whatever helpers it needs; `shared.py` is deleted. Every Base Chart now takes a fixed, minimal call — `population_layers`, `width`, `height`, `tweaks` (the **chart_inputs** contract, Functional Spec Section 10.0) — and returns image bytes only. `report_context` is no longer passed in; Selected-unit identity is read from the `"Selected"`-labelled `population_layers` entry instead, the same convention every chart now uses consistently. A chart file's self-containment is what makes it safe to hand whole to an external AI for editing.

**Custom Charts** extends the same idea: a user, typically via an AI, can save a new Base Chart into the workfile itself rather than the software (`custom_charts/`, Sections 5–6). A static check (`gate.py`) — allowed imports only, a few banned builtins disallowed, exactly one function matching the chart_inputs signature — runs before anything is compiled or executed; there is no sandboxing beyond this, and no check on what the function actually returns (only discoverable by running it). `resolve.py` looks up a `base_chart_name` against the built-in registry first, then a workfile's saved Custom Charts, so a saved one behaves identically to a built-in everywhere. `bundle.py` builds the document handed to an AI — the chart_inputs contract, a chart's complete current file (the whole module, not just the function, so nothing it depends on is silently dropped), and its live data.

### Decision 19 — Stat Tags: Anchor, Population Model, and Storage

A Stat Tag is a short, permanent, system-issued id (base-36, e.g. `[3]`, `[a7]`) standing in for one summary-stats value from one chart's own independently-authored cut of its cached data — defined and previewed on the Text tab (`ui/tabs/text_tab.py`), resolved by `update_text` at generation time (Decision 20).

**Anchor is `hex_id`, not `chart_ref`.** `chart_ref` (`Chart_0001` style) renumbers across non-deleted rows whenever the manifest table changes (delete, reimport) and is explicitly documented as never a storage key (Glossary). A tag typed into a template and anchored on `chart_ref` would silently start pointing at the wrong chart's data the first time the manifest renumbers, with nothing rewriting the already-placed template text. `hex_id` is the manifest's actual stable identity, so that's what a tag stores; `chart_ref`/title are resolved fresh, for display only, wherever the Text tab shows a chart picker.

**Populations is a single token, not a populations string.** A chart's populations string (Section 10.4) is deliberately an ordered set — several layers, because a chart renders several at once. A Stat Tag resolves to exactly one value, so it only ever needs one population. The Text tab enforces this with a `st.selectbox` (single choice), not the multiselect a chart's own populations control uses. An earlier iteration of this feature stored a multi-token populations string plus a `layer_index` (a 0-based token position, since `build_population_layers` always produces one layer per token in order) to identify which of several resulting layers a tag read from; once populations was restricted to a single token, every layer_index would always be `0`, so the field was removed as pointless rather than left as dead weight.

**Resolving `Region()`-style tokens dynamically, not by storing the resolved value.** An empty-bracket peer token (`Region()`, "the selected unit's own group") resolves to a concrete value (e.g. `"South East"`) only at the moment `build_population_layers` runs, for whichever unit is currently selected. Storing that resolved value as the tag's identity would freeze it — switching to an organisation in a different region would then fail to match anything, rather than correctly following the org's own, now-different, peer group. The token itself (`Region()`) is what's stored; resolution happens fresh every time, against the current reporting unit, via the same pipeline a chart uses (`cut_resolution.prepare_chart_cut` — Decision 22 — then `build_population_layers`). Display (`layer_display_label`, `stat_tags.py`) shows the token alongside its currently-resolved value for a dynamic token (`Region() — South East`), distinct from a genuinely static explicit-value token (`Region(Wales)`, shown as-is) — the two look different on screen precisely because they behave differently.

**Tag ids are a persisted, monotonically increasing base-36 counter** (`settings["next_stat_tag_id"]`), never recomputed from the surviving rows. Recomputing "one more than the current highest surviving tag" would let a freshly-issued tag reuse an id some other, still-untouched piece of template text already points at, the moment an earlier tag were deleted — the same never-reused guarantee `hex_id` already gives the manifest, just shorter and sequential rather than pseudo-random.

**Storage is a flat table, one row per tag** (`workfile_config/text_stats.csv`, Section 5) — `tag`, `hex_id`, `populations`, `start_period`/`end_period`/`metric_periods`, `reference_id`, `description`. No relational structure: several tags sharing the same underlying "cut" (same `hex_id`/populations/periods) each repeat those fields independently, the same way Running Order rows don't reference a shared "chart cut" object either. The Text tab's authoring form absorbs the repetition instead — a cut is defined once, then a checklist of that population's available Reference ids lets any number of tags be generated from it in one Add click, each still stored as its own independent row.

**Excel round-trip is full-replace, not identity-merge.** `stat_tags_xlsx.py` mirrors the Running Order xlsx's own simple pattern (download the current rows, edit, upload replaces the whole list) rather than the manifest table's `hex_id`-keyed add/update/soft-delete round trip — a Stat Tag has no cached data of its own to preserve behind a "deleted" flag, so a row absent from the uploaded file is simply gone, matching the Text tab's own Delete button. A row read back with a blank `tag` is issued a fresh one (`assign_missing_tags`) rather than left blank, since a blank tag could never be matched to anything anyway.

### Decision 20 — `update_text` Table-Cell Support

The one gap the Feature List previously flagged for `update_text` — `shape.table` cells being skipped — is closed. A python-pptx table cell (`_Cell`) exposes the same `.text_frame` interface (`.paragraphs`, `.runs`) as any other shape, so the existing paragraph-walk-and-collapse logic needed no table-specific handling — it was extracted into `_replace_tags_in_text_frame` (`text_engine.py`) and called against both `shape.text_frame` (where `shape.has_text_frame`) and every cell's own text frame (where `shape.has_table`, iterating `shape.table.rows`/`.cells`).

This closes the gap for every text tag, not just Stat Tags introduced this session — `[selected-reporting-unit-name]` in a table cell now resolves too, as a side effect of the same fix, since both tag families are folded into one combined token dict (`tokens`) before the presentation walk.

### Decision 21 — Charts Sheet Sandbox State Persistence

The Charts sheet's own control values (Section 9.3) previously lived only in `st.session_state`, discarded on every workfile Close, regardless of whether the workfile itself was saved — reopening always started from a blank sandbox, even for values never committed to a Running Order row via "Save to Running Order."

`capture_charts_sheet_state`/`_restore_charts_sheet_state` (`ui/tabs/charts_tab.py`) snapshot the sandbox's own current fields (bound row, cache file, chart type, populations, period range/metric-periods, tweaks, sizing, save-action/target) into a single new settings key, `charts_sheet_state`, as a JSON blob — captured just before every Save/Save As/Save and Close (sidebar.py, save_as_form.py), restored once per Open. Zoom is excluded (already documented as screen-only, never saved); an in-progress Custom Charts paste-back is excluded too (unvalidated, unsaved code — persisting it implicitly felt like the wrong default).

Restoration re-validates every field against what's actually available at Open time (rows, cache files, page sizes) rather than trusting it blindly — a Running Order regenerated by a template re-upload, or a chart deleted since, falls back cleanly instead of erroring. `clear_workfile_session_state` (`session_state.py`) now also wipes every `cs_`-prefixed session key on Open/Close, so a freshly opened workfile always restores from its own saved state (or starts blank) rather than inheriting a previous workfile's sandbox.

### Decision 22 — Cut Resolution Consolidation

Three call sites independently duplicated the same sequence — period-range trim, metric-periods conversion, population-table/target-rows/selected-ids resolution, then `build_population_layers` — against an already-loaded data shape: `insert_chart` (`assembly_engine.py`) against a Running Order row's own fields, the Charts sheet against its sandbox's own fields, and Stat Tags against a `text_stats.csv` row's own fields. Consolidated into `core/shared/normalisation_containers/cut_resolution.py`.

**Split into two functions, not one.** `prepare_chart_cut` does everything except the final `build_population_layers` call: it returns the trimmed/converted shape, the effective shape type (`"NumericSeries"` rather than the shape's own `"TimeSeries"` once a metric_periods conversion has actually applied — Decision 12), and `target_rows`/`selected_ids` ready to pass straight through. Callers call `build_population_layers` themselves. This split exists because the Charts sheet needs `target_rows` (for its own populations widget's peer-group options) *before* it knows which populations string it wants to resolve — bundling the final call into the shared function would have forced an ordering that only fit two of the three callers.

**Deliberately excludes loading the shape from cache.** That step differs meaningfully per caller (a Running Order row's `cache_file`; the Charts sheet's selected file; a Stat Tag's `hex_id`, translated to a cache filename) and each caller's own error-handling policy around it (`err_result`; a Streamlit warning; a silently skipped tag) — folding it in would have traded three clear call sites for one blurry one.

**Lives in `shared/normalisation_containers`, not `output_generation`.** None of the composed pipeline touches pptx, Streamlit, or the cache — it's pure data-shape normalisation, one level up from `population_layers.py` and `shape_transforms.py` (this composes them), the same tier. This forced two smaller relocations, since `shared` must not import from a higher layer (Section 2, one-way dependencies): `parse_metric_periods_string`/`build_metric_periods_string` moved from `output_generation/definition/running_order/dialog_support.py` to `shared/infrastructure/period_ids.py` (re-exported from `dialog_support.py` for existing callers), and `format_number`/`format_reference_value` moved from `ui/common/formatting.py` to `shared/infrastructure/value_formatting.py` (re-exported from `ui/common/formatting.py`), since `update_text`/Stat Tags — execution-layer code — needed the same formatting logic and couldn't import it from `ui`.

**Each caller keeps its own error-handling policy.** `prepare_chart_cut` raises `ValueError` (from the metric-periods conversion step) rather than swallowing it, so `insert_chart` still returns its own `err_result`, the Charts sheet still shows its own `st.error`, and Stat Tags still resolve to "unresolved" silently — behaviour identical to before the consolidation, only the duplicated code itself removed.

### Decision 23 — Output Tables: Grid Model, Anchor, and Storage

An Output Table is a grid of constant text and Stat Tag values, composited into a single image by a Base Table function (Decision 24) — the table equivalent of a chart, authored on its own tab (`ui/tabs/output_tables_tab.py`) rather than the Charts sheet, since an Output Table's content model doesn't fit `CHART_SANDBOX_FIELDS`.

**Grid layout, not a flat table.** The grid is stored in the same physical shape it's authored in — an (N+1) × (M+1) spreadsheet-shaped CSV, not a flat one-row-per-cell table (contrast Stat Tags, Decision 19). Row 0 and column 0 hold metadata (column widths, row heights, the table's own id in the corner cell); the remainder is content. Column widths/row heights are percentages of the table's own total width/height, each independently expected to sum to ~100% (validated on an explicit Update, tolerance ±0.5%, never auto-corrected — see Architecture, Structural Design Principles).

**Every Output Table starts at the same fixed size, and `table_id` is the only real identity.** Every Output Table — whether created via a `[Table]` yellow box or the Output Tables tab's own "+ New Output Table" form — starts at `grid_store.DEFAULT_TABLE_ROWS` × `DEFAULT_TABLE_COLUMNS` (7 × 4); there is no user-configurable Rows/Columns at creation time either way. A yellow box carries no name or size of its own any more (just the literal word "Table" — Functional Spec Section 6.3) and is never matched against an existing table on template re-upload: every occurrence, matched or free-floating, creates a brand-new table (`import_flow.merge_output_tables_from_template`), auto-named `Table_1`, `Table_2`, ... (never colliding with a name already in use), and sets `table_id` directly on the placeholder for `generate_from_template` to read. Re-uploading the same template twice therefore produces two independent sets of tables, not one reused set — accepted deliberately, since the box carries no identity of its own to key off; the user re-links Running Order rows to whichever set they want. `table_id` itself is a base-36 id from the shared `id_generation` counter (`settings["next_table_id"]`), the same never-reused guarantee `hex_id` and Stat Tags already have.

**Manually-created tables get automatic Running Order placement too.** Creating a table via "+ New Output Table" appends an `insert_table` row immediately above `save_ppt` (`row_ops.append_content_row_above_footer`) with no real slide/position — sizing defaults to 70%/50% width/height on the page-percentage scale, converted via `page_sizing.percent_to_emu`/`get_page_size_emu`. A blank `slide_index` is not a validation blocker: `insert_table` already errors gracefully per-row at run time if it's still unset when the batch runs (the same behaviour any row with missing required fields gets), so the user fixes position/slide afterwards via the Output Tables tab's own Preview sandbox or the Running Order tab, rather than being forced through that step before the row can exist at all.

**Content resolution reuses Stat Tags, not a new mechanism.** A cell holding a Stat Tag id (`[3]`) resolves via `text_engine.build_stat_tag_tokens` — the same token map `update_text` already builds — rather than a duplicated resolution path. Chart-component cells (`{3}`, referencing a Custom Chart-style saved visual embedded in a cell) are recognised by the grid's own grammar but not resolved or rendered — parked, see Feature List.

**`insert_table` mirrors `insert_chart`'s resolution, not its own scheme.** `table_type_ref` resolves built-in-then-custom via `custom_tables.resolve.get_table_callable`, the same pattern `insert_chart` uses via `get_chart_callable` for Custom Charts.

### Decision 24 — Base Tables as Standalone Artefacts, and Custom Tables

A Base Table is treated exactly the way a Base Chart is (Decision 18) — a rendering artefact, not application logic. Each of the ten built-ins is its own standalone file (`base_tables/{table_type_ref}.py`), carrying its own copy of whatever helpers it needs, no shared internal helpers module. Every Base Table takes a fixed, minimal call — **table_inputs**: `content` (already-resolved grid, Stat Tags substituted), `column_widths`, `row_heights`, `width`, `height`, `tweaks` — and returns image bytes only, the table equivalent of `chart_inputs`.

**No shape-type scoping.** Unlike a Base Chart, a Base Table isn't scoped to any one canonical data shape — every one takes the same already-resolved grid, so a saved Custom Table is a valid option everywhere, always, the moment it's saved. This is why `custom_tables/` (mirroring `custom_charts/` field for field — `contract.py`, `gate.py`, `resolve.py`, `bundle.py`) has no per-shape subfolder, unlike `custom_charts/`.

**Contract kept as its own copy, not shared with the chart domain.** `custom_tables/contract.py` defines its own allowed-imports whitelist and banned-names list, identical in content to the chart domain's today but deliberately not imported from it — `base_tables` and `base_charts` are independent rendering domains (Decision 18's own framing), and a future divergence in allowed libraries for one should carry no risk to the other.

### Decision 25 — Table and Chart Sizing: Unclamped Percent Conversion

`insert_table` and `assembly_engine._render_chart_image` convert a row's `width_emu`/`height_emu` into the percent-of-the-shorter-page-dimension value a Base Table/Base Chart function's `width`/`height` parameters expect, against a fixed 7.5-inch reference (`NARROWER_EMU = 6858000`). This conversion has no ceiling or floor: a table or chart's real placed size can legitimately be smaller or larger than that reference. An earlier version clamped the result to a 10–100 range — this caused a genuine loss of rendered resolution whenever a row's real physical size exceeded the reference (the image was generated at the clamped, smaller size, then stretched to its true, larger placement size on the slide), which is a defect, not a safeguard — see Architecture, Structural Design Principles ("Validate only where designed").

### Decision 26 — PDF Export Mechanism

`save_pdf` drives PowerPoint via COM automation (`comtypes`) and calls `Presentation.ExportAsFixedFormat(pdf_path, 2)` -- `FixedFormatType=2` (`ppFixedFormatTypePDF`), every other parameter left at its own default. `create_ppt` forces `autoCompressPictures="0"` on the presentation's own root XML element (`ppt/presentation.xml`) at the point the template is opened, the same flag PowerPoint's "Do not compress images in file" option controls, regardless of what the template file started with.

**Known limitation, accepted, for raster content.** A raster picture's resolution in the exported PDF can still render below its true source resolution -- understood to be inherent to PowerPoint's own PDF-writing engine, not something further settings or code changes on ChartGen's side currently resolve. This finding was established against `ExportAsFixedFormat`'s default settings specifically; an intermediate version used `SaveAs(pdf_path, 32)` (`ppSaveAsPDF`) instead on the same finding, before `ExportAsFixedFormat` was reinstated once every Base Chart and Base Table moved to SVG output (Decision 27), where this finding no longer applies to ChartGen's own generated images. It still applies to `insert_picture` (Functional Spec), which places arbitrary user-supplied raster images unchanged. See Feature List.

### Decision 27 — SVG Rendering Methodology for Base Charts and Base Tables

Every Base Chart and Base Table renders as SVG (matplotlib's own SVG backend, `fig.savefig(..., format="svg")`) rather than PNG, inserted into the PowerPoint template as a native SVG picture via a shared helper, `core/output_generation/execution/svg_insert.py` (`add_svg_picture`), used identically by `insert_chart` (`assembly_engine.py`) and `insert_table` (`tables/insert_table.py`).

**Why.** Both on screen and on PDF export, an embedded raster image renders visibly less crisply than PowerPoint's own native shapes and text, which stay crisp at any zoom, regardless of DPI or `autoCompressPictures` (Decision 26). SVG, being vector, has no such ceiling.

**Insertion mechanism.** `python-pptx`'s own `add_picture()` has no concept of SVG -- it only ever writes a single raster blip relationship. PowerPoint (2016+) stores an SVG picture as a dual-format blip instead: a fallback raster image (shown only by a viewer that doesn't understand the SVG extension) plus the SVG itself as a second, separate part, wired together via an `<a:extLst>` extension inside the picture's own `<a:blip>`, pointing at the SVG part's relationship id. `add_svg_picture` hand-builds this directly against the underlying `lxml` element tree, since `python-pptx` exposes no method for it.

**Font: Calibri, baked into vector outlines, not live text.** `matplotlib.rcParams["font.family"] = "Calibri"` is set in every Base Chart/Base Table file. `matplotlib.rcParams["svg.fonttype"]` is left at its own default, `"path"` -- text becomes vector outline shapes, not real `<text>` elements. The alternative (`"none"`, live text) was tried and reverted: neither PowerPoint's own Find nor either PDF export pathway exposed the text as genuinely searchable or selectable, and the PDF additionally showed characters selectable in mismatched positions, regardless of font availability.

**Known limitations, accepted.**
- Table/chart text is not searchable or selectable in PowerPoint or the exported PDF, regardless of `svg.fonttype` -- a structural limitation of how PowerPoint's Find and the PDF text layer treat an embedded picture's contents, not a tunable setting.
- Unhinted vector text can render thin vertical strokes (capital I, lowercase l, the pipe character) fractionally too heavy in some PDF viewers (confirmed in Adobe Reader) at low zoom; the effect disappears at higher zoom or in print. Cosmetic and zoom-dependent.

**DPI.** Base Tables retain `DPI = 300`, used only for matplotlib's own text-metric estimation during layout (`_text_width_inches`/`_text_height_inches`, which still rasterise to a throwaway offscreen figure to measure text extents) -- no bearing on the SVG's own resolution. Base Charts have no DPI constant, having no equivalent text-fit-measurement step.

**Scope.** Covers every built-in Base Chart and Base Table, and, via the `custom_charts`/`custom_tables` contract documents, every Custom Chart/Table saved from this point on -- one saved before this methodology must be re-saved to return SVG bytes and set Calibri, since both insertion call sites now assume SVG bytes unconditionally.
