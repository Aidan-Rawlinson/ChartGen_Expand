# ChartGen - Architecture

An overview: the two domains, the package layout, and how a report gets made.

Operative rules live in `CLAUDE.md` files next to the code they govern, not here. Formats and schemas are in [DATA_FORMATS.md](DATA_FORMATS.md). Terms are in [GLOSSARY.md](GLOSSARY.md). Scope and readiness are in [FEATURES.md](FEATURES.md).

---

## Structural design principles

These govern project structure, package and module layout, and naming. Not the code inside a file.

Project structure is the strongest, and in places the only, record of what the system is meant to be doing.

| Principle | What it means |
|---|---|
| Separation of concerns | Each package owns one job. If the job cannot be stated in a sentence, it is not one package |
| Legibility | Structure is the documentation. A reader should learn what the system does from folder and file names alone |
| High cohesion, low coupling | Things that change together live together. Things that do not need each other do not import each other |
| Explicit, one-way dependencies | No hidden reach-through, no circular imports. The dependency graph draws as an arrow diagram with no loops |
| Conventional Python layout | Standard `__init__.py`, import and naming conventions. Software domain only |
| Intention-revealing names | A name states the decision the package exists to make, not just what is inside it |
| Deliberately fine-grained | Finer than default Python convention. Bounded by separation of concerns: a split still needs its own reason to exist |
| Moderate, meaningful nesting | Depth encodes relationship. A sub-package states that it belongs to its parent and is its own concern within it |
| Validate only where designed | Input validation, clamps and defensive guards are an architectural decision, not a local coding choice. Raise before adding one |

---

## Two domains

| Domain | What it is | Lifecycle |
|---|---|---|
| **Software** | The installed application: code, static config, one per-machine setting | Persists across every project and session until reinstalled or updated |
| **Workfile** | One workfile's complete footprint: the `.cgw`, its sibling `.pptx`, its `outputs/` and `CG_Extracts/` folders, and the in-memory working copy while open | The on-disk part persists once saved and is shareable. The in-memory copy exists only between Open and Close |

**Defining rule.** The Software domain does not change as a result of workfile work. Opening a workfile, fetching data, editing the Running Order and running batches touch none of the installed application. The Software domain changes only as a function of which user is signed in on this machine.

The one exception is the last-used username in `chartgen/session_shell/auth/credentials.csv`, rewritten on each successful sign-in. No password or token is ever written to disk.

Memory is not a third domain. It is the Workfile domain's in-session form.

---

## Layout

```
ChartGen_Expand/
├── app.py                          Streamlit entry point
├── run_chartgen.bat                launcher, creates the venv on first run
├── requirements.txt
├── .streamlit/
├── docs/
├── installer/
├── user_resources/
└── chartgen/
    ├── session_shell/
    │   ├── auth/                   login.py, credentials.csv
    │   └── lifecycle/              concurrency.py, startup_file.py, update_check.py
    ├── workfile/
    │   ├── setup/                  new_workfile.py, save_as.py
    │   └── state/                  workfile_file.py, session_state.py
    ├── acquisition/
    │   ├── import_flow.py, url_triage.py, fetch_dispatch.py
    │   ├── manifest_table/         xlsx_writer.py, xlsx_reader.py
    │   ├── toolkit_nhs/            api_client, fetch, transformers, peer_groups,
    │   │                           population_tables, table_naming, submission_codes
    │   ├── toolkit_indicators/     api_client, fetch, transformers, url_parser,
    │   │                           population_tables, table_naming
    │   └── template/               template_reader.py, url_parser.py
    ├── output_generation/
    │   ├── static_config/          chart_type_map.csv
    │   ├── definition/
    │   │   └── running_order/      schema, dialog_support, generation, row_ops,
    │   │                           xlsx_writer, xlsx_reader
    │   └── execution/
    │       ├── assembly_engine.py, batch_process.py, results.py, svg_insert.py
    │       ├── charts/
    │       │   ├── cache_reader, chart_type_map, chart_store, chart_store_xlsx
    │       │   ├── base_charts/    one folder per shape, registry.py
    │       │   └── custom_charts/  contract, gate, resolve, bundle
    │       ├── tables/
    │       │   ├── grid_store, resolve, grid_xlsx, insert_table
    │       │   ├── base_tables/    registry.py
    │       │   └── custom_tables/  contract, gate, resolve, bundle
    │       ├── pictures/           insert_picture.py
    │       ├── excel/              insert_from_excel.py
    │       ├── pptx_com/           position_finder.py
    │       └── text/               text_engine.py, stat_tags.py, stat_tags_xlsx.py
    ├── shared/
    │   ├── normalisation_containers/
    │   │   ├── shapes/             one module per shape, common, dispatch,
    │   │   │                       reference_ids
    │   │   └── population_layers, peer_group_tokens, shape_transforms, cut_resolution
    │   └── infrastructure/         constants, report_context, soft_parents, page_sizing,
    │                               cache_writer, cg_extracts, population_table_xlsx,
    │                               value_formatting, period_ids, id_generation,
    │                               version_compatibility, render_scale
    └── ui/
        ├── common/                 formatting, pickers, guidance, layout_css, compact_layout
        ├── auth/                   login_form.py
        ├── workfile/               sidebar, dialogs, new/open/save-as/update forms
        └── tabs/                   imports, populations, select, text, running_order,
                                    outputs; charts_tab/ and output_tables_tab/ are
                                    packages, one module per section of the sheet
```

Layer order is `ui` above `output_generation` above `acquisition` above `shared`. Imports go one way only.

| Package | Owns |
|---|---|
| `session_shell` | Sign-in, the advisory lock, file association, update check |
| `workfile` | The `.cgw` format and the in-session `WorkfileState` |
| `acquisition` | Two toolkit APIs, template reading, the manifest table |
| `output_generation/definition` | The Running Order: schema, generation, row operations, xlsx round-trip |
| `output_generation/execution` | Running a Running Order: dispatch, rendering, PowerPoint output |
| `shared/normalisation_containers` | The canonical data shapes and population resolution |
| `shared/infrastructure` | Generic helpers that know nothing about charts, toolkits or the UI |
| `ui` | Streamlit only. Business logic is delegated to the owning module |

Two modules sit deliberately outside the package they serve, because they need to know about siblings that must not know about each other: `url_triage.py` and `fetch_dispatch.py` above both toolkits, and `shape_transforms.py` above the shapes.

---

## How a report gets made

**Acquisition.** A template upload or a direct Excel entry puts a URL into the manifest table, classified `nhs` or `indicators` on the way in. Fetch pulls each URL through its own toolkit's transformer into a canonical data shape, builds or merges that project's population tables, and writes the shape to the cache.

**Definition.** Template processing produces the cleaned `.pptx`, records each yellow box's position, and generates a Running Order: an ordered table of function rows. The user edits it on the Running Order tab, in Excel, or through the Charts sheet and Output Tables sandboxes.

**Execution.** `batch_process` splits enabled rows by scope and iterates the units in the run. For each unit, `assembly_engine.run_running_order` dispatches each row through `FUNCTION_MAP`:

```
create_ppt              open the cleaned template
insert_chart            load the shape from cache
                        prepare_chart_cut     trim periods, resolve the population
                        build_population_layers
                        get_chart_callable    built-in, or a saved Custom Chart
                        the chart function    returns image bytes
                        add_svg_picture       place it on the slide
insert_table            resolve the grid, render a Base Table, layer any chart cells
update_text             walk the presentation, replace every tag
save_ppt / save_pdf     write the output
```

Charts render in memory. The only disk writes in a run are the final saves.

---

## Where the rest is written

| Subject | Where |
|---|---|
| Standing rules, layer order, how to run | [CLAUDE.md](../CLAUDE.md) |
| Dependency rules and relocation shims | `chartgen/shared/CLAUDE.md` |
| The render contracts and the scaling mechanism | `chartgen/output_generation/execution/charts/base_charts/CLAUDE.md` |
| Chart-cell geometry and the bbox trap | `chartgen/output_generation/execution/tables/base_tables/CLAUDE.md` |
| Yellow box and fill colour resolution | `chartgen/acquisition/template/CLAUDE.md` |
| Each toolkit's own rules | `chartgen/acquisition/toolkit_nhs/CLAUDE.md`, `toolkit_indicators/CLAUDE.md` |
| Population layer and cut resolution | `chartgen/shared/normalisation_containers/CLAUDE.md` |
| Adding a shape or a shape-level field | `chartgen/shared/normalisation_containers/shapes/CLAUDE.md` |
| Ids, counters and version compatibility | `chartgen/shared/infrastructure/CLAUDE.md` |
| COM automation rules | `chartgen/output_generation/execution/pptx_com/CLAUDE.md`, `excel/CLAUDE.md` |
| Session state and the percent boundary | `chartgen/ui/CLAUDE.md` |
| State ownership and locking | `chartgen/workfile/CLAUDE.md` |
| Every schema and id convention | [DATA_FORMATS.md](DATA_FORMATS.md) |
| Every term | [GLOSSARY.md](GLOSSARY.md) |
| Scope, readiness and known limitations | [FEATURES.md](FEATURES.md) |
