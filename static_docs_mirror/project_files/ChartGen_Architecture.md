# ChartGen — Architecture

*TBN Internal · Input document for refactoring — describes the current system only*

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
    │   ├── toolkit_nhs/
    │   │   ├── api_client.py
    │   │   ├── fetch.py
    │   │   ├── transformers.py
    │   │   ├── cache_writer.py
    │   │   └── peer_groups.py
    │   └── template/
    │       ├── template_reader.py
    │       └── url_parser.py
    ├── output_generation/
    │   ├── static_config/
    │   │   └── chart_type_map.csv
    │   ├── definition/
    │   │   └── running_order/
    │   │       ├── schema.py, dialog_support.py, generation.py,
    │   │       └── xlsx_writer.py, xlsx_reader.py
    │   └── execution/
    │       ├── assembly_engine.py
    │       ├── batch_process.py
    │       ├── results.py
    │       ├── charts/
    │       │   ├── base_charts/
    │       │   │   ├── shared.py, numeric_series.py, numeric_compositional.py,
    │       │   │   └── categorical_compositional.py, registry.py
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
    │   │   │   └── categorical_compositional.py, dispatch.py
    │   │   ├── population_layers.py
    │   │   └── peer_group_tokens.py
    │   └── infrastructure/
    │       ├── constants.py
    │       └── report_context.py
    └── ui/
        ├── common/
        │   ├── formatting.py
        │   └── pickers.py
        ├── auth/
        │   └── login_form.py
        ├── workfile/
        │   ├── sidebar.py, workfile_dialogs.py, new_workfile_form.py,
        │   └── open_workfile_form.py, save_as_form.py
        └── tabs/
            ├── details_tab.py, config_tab.py, imports_tab.py, select_tab.py,
            └── text_tab.py, running_order_tab.py, charts_tab.py, outputs_tab.py
```

| Path | Notes |
|---|---|
| `app.py` | Streamlit entry point — sequences auth, sidebar, dialogs, and tabs; holds no UI construction or business logic of its own |
| `run_chartgen.bat` | Double-click launcher; creates venv on first run |
| `requirements.txt` | Python dependencies (kept in sync with `.bat`) |
| `user_resources/PPT_Template_Creation.md` | Guidance doc for template designers |
| `core/session_shell/auth/` | Credential validation, token handling, last-used-username persistence (mechanics only). `credentials.csv` is ★ the one genuine exception to the software/workfile split, see Decision 7 |
| `core/session_shell/lifecycle/concurrency.py` | Lock-state classification and Open/Open Read-Only mechanics for the workfile advisory lock |
| `core/workfile/setup/new_workfile.py` | New Workfile flow — fetches submissions/organisations for a chosen project/year, builds the units table with `Region()` assignment |
| `core/workfile/setup/save_as.py` | Save Workfile As — cleaned-template copy, lock transfer/release, and the read-only-session-must-choose-a-different-folder rule |
| `core/workfile/state/workfile_file.py` | Owns the `.cgw` format — see Section 5. The only module that reads/writes the ZIP directly. Also owns `UNITS_FIELDNAMES`, the units.csv column schema |
| `core/workfile/state/session_state.py` | Streamlit-side `WorkfileState` accessors — Streamlit-rerun plumbing only |
| `core/acquisition/import_flow.py` | Coordinator: sequences template read → URL merge → fetch → Running Order generation. The only module that imports both `acquisition` and `output_generation.definition` |
| `core/acquisition/toolkit_nhs/` | Fetch → canonical data shapes (API client, transformers, cache writer, peer-group menu-building) |
| `core/acquisition/template/` | Reads `.pptx` placeholders; detects/strips yellow boxes; parses toolkit URLs |
| `core/output_generation/definition/running_order/` | Split by concern: schema (`schema.py`), row-edit dialog support (`dialog_support.py`), template-generation (`generation.py`), and `.xlsx` export/import (`xlsx_writer.py`, `xlsx_reader.py`). Package `__init__.py` re-exports the full API, so external call sites are unaffected |
| `core/output_generation/execution/assembly_engine.py` | Executes one report's normal-scope Running Order rows via dispatch table. Not the only module touching `python-pptx` — `insert_picture` and `insert_from_excel` also do |
| `core/output_generation/execution/batch_process.py` | Batch loop — splits enabled Running Order rows by scope (`batch_open`/`normal`/`batch_close`) and iterates `assembly_engine.run_running_order` across the units in a run |
| `core/output_generation/execution/results.py` | `ok_result` / `err_result` — kept local to `execution`, not shared globally |
| `core/output_generation/execution/charts/` | 17 Base Charts, split into `base_charts/` by canonical data shape (`numeric_series.py`, `numeric_compositional.py`, `categorical_compositional.py`), with shared palette/helpers in `shared.py` and dispatch in `registry.py`; cache reading |
| `core/output_generation/execution/pictures/insert_picture.py` | `insert_picture` Running Order function |
| `core/output_generation/execution/excel/insert_from_excel.py` | Excel COM capture (`open_excel` / `insert_from_excel` / `close_excel`) |
| `core/output_generation/execution/text/text_engine.py` | `update_text` Running Order function — promoted out of `assembly_engine` to its own module |
| `core/output_generation/static_config/chart_type_map.csv` | Data shape → valid chart type refs (developer-owned, read-only) |
| `core/shared/normalisation_containers/` | NumericSeries / NumericCompositional / CategoricalCompositional, split into one module per shape under `shapes/`, each owning its shape's canonical Metric-Series stats computation and autotable statistics (plus `common.py` for the shared `Unit`/`ShapeStats` base and `dispatch.py` for `filter_shape`/`autotable_stats`); `build_population_layers`; the shared peer-group token rule |
| `core/shared/infrastructure/constants.py` | `coerce_row` / `FIELD_TYPES` — generic CSV/WorkfileState field-type coercion, used by `api_client`, `running_order`, and `workfile_file` |
| `core/shared/infrastructure/report_context.py` | `ReportContext` + `build_report_context()` |
| `core/ui/` | Streamlit UI, grouped into `common/` (generic display/picker helpers), `auth/` (sign-in widget), `workfile/` (sidebar, dialogs, New/Open/Save As forms), and `tabs/` (the eight tab renderers). Business logic delegated to the owning module rather than living here |

---

## 5. Workfile Domain — On Disk (`.cgw`)

A single workfile's complete, portable, shareable state. Internally a ZIP archive — the same pattern as `.pptx`, `.docx`, `.xlsx`.

```
MyWorkfile.cgw  (ZIP)
├── workfile_config/
│   ├── settings.csv
│   ├── urls.csv
│   ├── units.csv
│   └── running_order.csv
├── data_cache/
│   ├── manifest.json
│   └── {tier_id}_{group}_{option}.json
├── template/
│   └── MyWorkfile.pptx
└── workfile_info.json
```

| Path | Notes |
|---|---|
| `workfile_config/settings.csv` | key,value — paths, year, project_id, batch_cursor, etc. |
| `workfile_config/urls.csv` | Toolkit URLs (populated by yellow-box extraction) |
| `workfile_config/units.csv` | Population table — one row per reporting unit, `Region()` column |
| `workfile_config/running_order.csv` | ★ Canonical Running Order store — flat table, not `.xlsx`. The `.xlsx` is generated from this on demand for download and parsed back into it on upload; it is never itself written to this archive |
| `data_cache/manifest.json` | Index: tier_id, group, option, label, shape_type, url, last_fetched — per cached chart |
| `data_cache/{tier_id}_{group}_{option}.json` | One file per fetched chart — serialised data shape |
| `template/MyWorkfile.pptx` | Reference copy of the cleaned template — validation only. Never run from. Compared against the live sibling `.pptx` (below) to warn on structural drift |
| `workfile_info.json` | Stored uncompressed (`ZIP_STORED`) — cheap to read alone, before the rest of the archive loads. Contains `workfile_name`, `last_saved_by`, `last_saved_at`, `chartgen_version`, `locked_by` (advisory concurrency), `locked_at` (see Decision 4) |

**Running Order column schema** (`running_order.csv`):

| Column | Description |
|--------|-------------|
| `row_id` | Unique integer row identifier (1-based) |
| `enabled` | 1 / 0 — disabled rows are skipped at runtime |
| `scope` | `normal` / `batch_open` / `batch_close` — when the row executes relative to a batch |
| `function` | Function name to call |
| `slide_index` | 0-based slide index (blank for structural functions) |
| `placeholder` | Placeholder name, e.g. `Chart 1` (blank for structural functions) |
| `chart_type_ref` | Base Chart function name, e.g. `ranked_column` (blank for non-chart rows) |
| `cache_file` | JSON cache filename supplying data for this chart (blank for non-chart rows) |
| `populations` | Per-row populations string, overriding the project default (blank to use the default) |
| `image_path` | Source image path for `insert_picture`; may contain `[code]`/`[id]` tokens |
| `excel_path` | Workbook path for `open_excel` / `insert_from_excel` / `close_excel` |
| `export_range` | Excel named range captured as an image by `insert_from_excel` |
| `driver_range` | Excel named range receiving the current `unit_id` |
| `left_emu` | Left position in EMU — populated from template |
| `top_emu` | Top position in EMU — populated from template |
| `width_emu` | Width in EMU — populated from template |
| `height_emu` | Height in EMU — populated from template |
| `notes` | Free text; user reference only, ignored at runtime |

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

**CSV vs JSON.** `running_order.csv`, `units.csv`: flat, fixed-column, one-row-per-entity — CSV's natural shape, and legible to a non-technical colleague who renames `.cgw` to `.zip`. `data_cache/*.json`: nested (serialised dataclasses), never hand-edited. Intentional split, not an inconsistency.

---

## 6. Workfile Domain — In Memory (Runtime)

What exists only while the application is running, for the duration of one open session. Built and discarded; never written to disk except via the explicit Save action (the Workfile domain's on-disk form) or the explicit `save_ppt`/`save_pdf` Running Order functions (their own output, not this domain's own state).

```
Streamlit process (st.session_state)
├── st.session_state["ws"] → WorkfileState
│     workfile_path, workfile_name
│     settings: dict
│     urls: list[dict]
│     units: list[dict]
│     running_order_rows: list[dict]
│     manifest: dict
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
    │     default_populations: str
    │     excel_workbooks: dict
    │
    ├── ReportContext
    │     unit_id: int
    │     unit_code: str
    │     unit_name: str
    │     organisation_id: str
    │     organisation_name: str
    │
    └── list[NumericSeries | NumericCompositional | CategoricalCompositional]
          population_label: str  — set per layer by build_population_layers
```

| Item | Notes |
|---|---|
| `st.session_state["ws"]` → `WorkfileState` | ★ The working copy of the open `.cgw` |
| `WorkfileState.settings: dict` | Mirrors `workfile_config/settings.csv` |
| `WorkfileState.running_order_rows: list[dict]` | ★ Sole live copy — see Section 5 note |
| `WorkfileState.manifest: dict` | Mirrors `data_cache/manifest.json` |
| `WorkfileState.cache: dict` — `{filename: json_string}` | Mirrors `data_cache/*.json` |
| `WorkfileState.dirty: bool` | Not persisted — session-only flag |
| `WorkfileState.read_only: bool` | Not persisted — session-only. True only for a session opened via Open Read-Only; such a session never writes or clears the lock. |
| `st.session_state["token"]` | API session token (Decision 7) — never the password |
| `st.session_state[...UI flags...]` | `show_new_form`, `ro_selected_idx`, etc. — disposable, no domain meaning beyond this widget render |
| Per-batch-run objects | Live only for the duration of one Run Selected / Run Batch / Run All call — constructed fresh, discarded after |
| `AssemblyContext` | One per **batch** (persists across reports within it) |
| `AssemblyContext.report_context: ReportContext` | Rebuilt per report, see below |
| `AssemblyContext.excel_workbooks: dict` | Added dynamically by `open_excel`, Insert From Excel |
| `ReportContext` | One per **report** (rebuilt fresh per unit, from the per-report settings dict, never from `load_settings()` — batch overrides apply correctly) |
| `list[data shape]` | One list per `insert_chart` call — built fresh by `build_population_layers()` each time; each entry is a filtered copy of the chart's data shape, stats recalculated |
| `population_label: str` | Field on the data shape itself — e.g. `"All"`, `"Selected"`, or a resolved peer-group value |

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
| **New Workfile** | Prompts for save location and name, then runs the New Workfile flow. Submissions fetch is the final blocking step. |
| **Open Workfile** | File picker for `.cgw`. Always leads to a decision step naming the lock state before the workfile loads, offering Open or Open Read-Only. Open writes the lock; Open Read-Only does not. |
| **Save** | Serialise `WorkfileState` to ZIP, update `workfile_info.json`. No confirmation dialog. Disabled in a Read-Only session. |
| **Save As** | New folder/name via native picker. Copies the cleaned template alongside the new `.cgw` under the matching name; releases the lock on the old file, writes a new one. Outputs are not carried across. In a Read-Only session, the target folder must differ from the original workfile's; on success the session becomes normal, and the old file's lock is released only if this session had held it. |
| **Save and Close** | Save, then clear `locked_by`+`locked_at`, return to no-workfile-loaded state. Disabled in a Read-Only session. |
| **Close Without Saving** | Confirms if dirty. Clears the lock; ZIP otherwise untouched. Skips the confirmation in a Read-Only session — closes immediately regardless of unsaved edits. |

Buttons are active/inactive based on the state of the software.

**Crash.** Lock fields remain as last written. The next user opening the workfile sees the stale lock as the same decision step described above.

**Read-Only sessions.** Offered on every Open regardless of lock state. Enforcement is shallow: Save is disabled; every other action behaves as normal, so unsaved edits are lost unless rescued via Save As. A Read-Only session never writes the lock, and therefore never clears one on close.

### Decision 7 — Credentials Location

Only the username is stored, in `core/session_shell/auth/credentials.csv` — rewritten on every successful login, saving the user from re-entering it on next launch. The password and session token are never persisted to disk; the token lives only in `st.session_state["token"]` for the session's duration.

This is per-machine, per-user data, not workfile data, so it lives in `session_shell/auth/` rather than the workfile or static config.

### Decision 8 — SharePoint Compatibility

ChartGen is designed for a SharePoint-hosted team environment accessed via OneDrive sync.

Charts render entirely in memory as bytes; the only disk writes during a batch run are the final `save_ppt`/`save_pdf` calls, one per report. The `.cgw` is read once at the start of a run and not written again until Save. This avoids the small, rapid file writes that trigger OneDrive sync issues, and leaves the sync client nothing to lock mid-run.

Files accessed via OneDrive sync appear as ordinary local filesystem paths to Python — `zipfile`, `open()`, `shutil` all work unmodified. This avoids the filesystem-API incompatibilities that affect COM/VBA approaches against SharePoint's virtual file system.

### Decision 9 — Application Location (Interim)

For the current phase, ChartGen lives in a folder on the C: drive under direct developer control. No installer, no registered file associations yet. File association for `.cgw` and a proper installer (e.g. Inno Setup) are deferred until the application is stable enough to warrant a more professional distribution approach.
