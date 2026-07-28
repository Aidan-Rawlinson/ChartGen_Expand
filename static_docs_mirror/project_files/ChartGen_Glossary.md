# ChartGen — Glossary

*TBN Internal · Naming and taxonomy — the terms used consistently across the other documents.*

---

## Python Terminology (General)

*Standard Python packaging terminology — not specific to ChartGen. Established for use across the Project Structure Review and beyond.*

| Term | Definition |
|---|---|
| **Package** | Any folder with `__init__.py`. |
| **Sub-package** (also: nested package) | A package nested inside another package. |
| **Parent package** | A package containing one or more sub-packages, relative to those sub-packages. |
| **Top-level package** | A package that sits directly under the project root, not nested inside another. |
| **Module** | A `.py` file. |
| **Package data** | Non-Python files sitting inside a package. |
| **Directory** (also: folder) | Any folder without `__init__.py`. |
| **Codebase** | All the code that exists — the content, not its arrangement. |
| **Project structure** (also: directory structure, folder structure, project layout) | The arrangement of packages, modules, and directories relative to each other. |

---

## Package Map

Top-level structure only. See Architecture, Sections 3–4, for descriptions.

```
Software Domain
chartgen/
├── app.py
├── run_chartgen.bat
├── requirements.txt
├── user_resources/
└── core/
    ├── session_shell/
    │   ├── auth/
    │   └── lifecycle/
    ├── workfile/
    │   ├── setup/
    │   └── state/
    ├── acquisition/
    │   ├── import_flow.py
    │   ├── url_triage.py
    │   ├── fetch_dispatch.py
    │   ├── toolkit_nhs/
    │   ├── toolkit_indicators/
    │   └── template/
    ├── output_generation/
    │   ├── static_config/
    │   ├── definition/
    │   └── execution/
    │       ├── charts/
    │       ├── pictures/
    │       ├── excel/
    │       └── text/
    ├── shared/
    │   ├── normalisation_containers/
    │   └── infrastructure/
    └── ui/

Workfile Domain (.cgw)
MyWorkfile.cgw  (ZIP)
├── workfile_config/
├── data_cache/
├── template/
└── workfile_info.json
```

---

## Business & Reporting Domain

### Comparative analysis domain

- **Normalisation** — bringing data from different sources into a single, consistent structure and format. See the Primer, Section 3; see also Data shape.

- **Peer group** — a named subset of the population, defined by a `Name()` column (e.g. `Region()`, `Shelford Group()`). A unit with no group for that column is marked `x` (or left blank) rather than assigned one. See Functional Spec, Section 7.2.

- **Population** — the set of units being compared. A single output may include analysis of multiple different populations, usually in a hierarchical relationship (e.g. Regions, Organisations, and Emergency Departments). See the Primer, Section 3.

- **Selected unit(s)** — the unit or units that are the current focus of a comparative analysis, examined in the context of the wider population they sit within. May also be the reporting unit, but does not have to be. E.g. a report for an organisation could have a chart where an Emergency Department is the selected unit.

- **Summary statistics** — numeric values describing a population's data (e.g. mean, median, quartiles, peer averages). See also Autotable.

- **Unit** — a single organisation or entity being compared against others within a population. Will often, but not always match to project submissions. Reporting unit is the named special case used for the organisation an output is being generated for. See the Primer, Section 3.

### ChartGen scope & reporting

- **Algorithmic Report** — a report whose structure itself varies per unit based on conditional logic, not just the data within a fixed structure.

- **Bespoke Narrative** — per-unit written narrative generated for each report. This could be a lookup of human written narrative, algorithmically selected, AI generated, or a combination of these or other approaches.

- **Individualised Report** — a report with a fixed structure, but data varying per instance.

- **Output** — a generated PowerPoint or PDF deliverable produced by ChartGen. Preferred over "report" where possible, as it also includes slide packs, fliers, and presentations.

- **Project** (TBN usage) — a single benchmarking exercise with its own data collection, population, and reporting cycle, identified by a `project_id` and `year`. TBN consistently uses "project," not "programme," for this concept.

- **Reporting unit** — the individual unit (typically an organisation or site) that an output is being generated for; a named special case of Unit.

---

## ChartGen System & Architecture Terms

### Cluster 4 — File & session structure

- **`.cgw`** — ChartGen Workfile file. A ZIP archive containing all of one workfile's saved state. See the Architecture document, Section 4, for full internal structure.

- **Chart ref (`chart_ref`)** — the human-facing display index for a chart in the manifest table (`Chart_0001` style). Renumbered across non-deleted rows whenever the table changes; never used as a storage key. See Hex id.

- **Data Cache** — the physical, on-disk store of fetched chart data: the manifest table (`manifest.csv`) and one JSON file per chart, named by `hex_id`, inside the `.cgw`. Constitutes the data side of the Workfile domain when the file is closed. Mirrored in memory by `WorkfileState.cache`/`.manifest_rows` while the workfile is open.

- **File version id** — the version identifier for the `.cgw`'s internal structure, stamped into `workfile_info.json` at Save. Independent of the software id — a structure change needs a new file version id regardless of the software id. See Functional Spec, Section 5.1.

- **Hex id (`hex_id`)** — a chart's stable internal identity in the manifest table: five uppercase hexadecimal digits, unique within the workfile, never reused and never renumbered. Names the chart's cache file and is the round-trip identity for Excel edits. See Architecture, Section 5.

- **Manifest table (`manifest.csv`)** — the chart URL table: the canonical index of every chart in a workfile, one row per URL, held at `data_cache/manifest.csv` inside the `.cgw`. Populated by template extraction and direct user entry. See Architecture, Section 5, for the column schema.

- **Read-Only** — a workfile session opened without claiming the advisory lock. Only Save is disabled; every other action behaves as in a normal session. See Functional Spec, Section 5.

- **Software id** — the version identifier for an installed build of ChartGen itself, distinct from the file version id. See Functional Spec, Section 5.1.

- **Stat tags table (`text_stats.csv`)** — the table indexing every Stat Tag (see Cluster 8) defined in a workfile, one row per tag, held at `workfile_config/text_stats.csv` inside the `.cgw`. Mirrored in memory by `WorkfileState.text_stats_rows` while the workfile is open. See Architecture, Section 5 and Decision 19.

- **WorkfileState** — the in-memory Python object holding the complete working state of an open `.cgw`. The sole interface other packages use to read or write workfile data during a session. See the Architecture document, Section 5.

### Cluster 5 — Template & placeholders

- **Cleaned template** — the version of a `.pptx` template with all yellow annotation textboxes stripped out. The Assembly Engine always runs from this version, never the original marked-up template.

- **Free-floating yellow box** — a yellow box with no overlap with any placeholder on its slide. Its own position and size stand in for a placeholder's. See Functional Spec, Section 6.3, and Architecture, Decision 13.

- **Placeholder** — a PowerPoint placeholder ChartGen recognises by its native type (Content, Picture, Chart, Clip Art, Table, SmartArt, or Media), not by its name. A native Text placeholder is not in this set — it is populated only by text tag replacement, never the yellow-box convention. See Functional Spec, Section 6.2.

- **Yellow textbox convention** — the template-authoring method of placing a yellow-filled textbox to associate it with a data source (URL), image path, or Excel range. Resolved against the slide's placeholders into one of three outcomes — fully contained, free-floating, or ambiguous partial overlap. See Functional Spec, Section 6.3, and Architecture, Decision 13.

### Cluster 6 — TBN Toolkit structures

- **Denominator (TBN Toolkit)** — a variable and URL component that enables webpages to include multiple data sources/calculations. Most commonly used to vary the denominator value, but can change numerators and calculations as well.

- **Service (TBN Toolkit)** — part of the TBN project process enabling multiple questionnaires per project. A URL component.

- **Tier (TBN Toolkit)** — a component of the toolkit structure which hosts charts.

- **Indicators toolkit** — the second toolkit data source (timeseries data), distinct from the NHS toolkit above — a different API host and URL shape. Chart URLs are classified into it by manifest rows with `database = "indicators"`, decided by `url_triage.url_to_database` from the URL's path shape. See Architecture, Decision 10.

### Cluster 7 — Data shapes & populations

- **Chart data** — a comparative dataset for a specific analysis. Called "chart data" because it typically originates from a chart fetch and ends up rendered in a chart, but the data itself is agnostic to that flow and could be, for example, used in tables.

- **Data shape** — a data container for normalised chart data. See Functional Spec, Section 8.

- **Population label (`population_label`)** — a field on the data shape itself identifying which population layer a filtered copy represents (e.g. `"All"`, `"Selected"`, a resolved peer-group value), set by `build_population_layers`. See Functional Spec, Section 10.4, and the Architecture document, Section 5.

- **Populations string** — the `^`-delimited ordered list of tokens (e.g. `All^Region()^Selected`) that specifies which population layers are sent to the chart engine. Every non-blank token always produces its own population layer, even one that resolves to zero units — a token is never dropped for lacking data. See Functional Spec, Section 10.4.

- **Summary stats** — the statistics a data shape computes for itself, independent of any visualisation (e.g. `numeric_series_summary_stats`); read per population layer via `summary_stats_by_layer`, called directly against the relevant population layers by whichever consumer needs it (the Charts sheet display being the only current one), and displayed there with a Reference id alongside each figure. Distinct from the general "Summary statistics" concept above; this is the specific technical term for the data itself. See Functional Spec, Section 9.4, and Architecture, Decisions 15 and 17.

- **Period (`period_id`, `period_label`)** — a single point on a TimeSeries shape's period axis, shared across every Metric-Series in that shape. See Functional Spec, Section 8.2.

### Cluster 8 — Running Order & execution

- **Batch** — processing multiple outputs in a single run.

- **Charts sheet round-trip fields (`CHART_SANDBOX_FIELDS`)** — the maintained list of Running Order columns the Charts sheet reads from, and writes back to, a chart row: `chart_type_ref`, `cache_file`, `populations`, `start_period`, `end_period`, `metric_periods`, `width_emu`, `height_emu`, `tweaks`. See Architecture, Decision 11.

- **Enabled column** — the per-row on/off switch in the Running Order. Stored as an integer `1`/`0` at runtime.

- **Page size (workfile)** — the associated PowerPoint template's slide width and height, captured once at template processing and held in workfile settings (`template_page_width_emu`, `template_page_height_emu`). The reference dimension for the Charts sheet's percent-of-shorter-dimension sizing unit. See Architecture, Decision 11.

- **Running Order** — the user-authored, row-based instruction table that defines report assembly: function, parameters, control flag. See Functional Spec, Section 9, and the Architecture document, Decision 1, for storage format.

- **Scope (`normal` / `batch_open` / `batch_close`)** — the Running Order column controlling when a row executes relative to a batch: once per report (`normal`), once before the whole batch (`batch_open`, e.g. `open_excel`), or once after (`batch_close`, e.g. `close_excel`).

- **Stat tag** — a short, permanent, system-issued id (base-36, e.g. `[3]`, `[a7]`) standing in for one summary-stats value from one chart's own independently-authored cut of its cached data — a single population token, optional TimeSeries period range/metric-periods conversion, and a Reference id (see Cluster 10). Defined and previewed on the Text tab; resolved by `update_text` at generation time, in ordinary text and PowerPoint table cells alike. Not tied to any Running Order row. Distinct from Text Tag (below) — a Reference id isn't globally unique, so a Stat Tag needs hex id + population + reference id to mean anything, where a Text Tag needs nothing beyond its own literal string. See Functional Spec, Section 12.1, and Architecture, Decision 19.

- **Text Tag** — a placeholder string embedded in template text (e.g. `[selected-reporting-unit-name]`) replaced with a per-unit value at generation time by `update_text`.

### Cluster 9 — Runtime objects

- **AssemblyContext** — the in-memory object the Assembly Engine builds once per batch run, carrying the open `Presentation` object, output path, run log, the current `ReportContext`, the current `Full Unit Set`, default populations string, and any open Excel COM workbook references. See the Architecture document, Section 5.

- **Full Unit Set** — for the current reporting unit, its own row plus every row related to it one hop out (via `soft_parents`, both directions), keyed by table name — `{table_name: [row, ...]}`. Rebuilt once per report, alongside `ReportContext`. `insert_chart` looks up a chart's own `population_table` in the Full Unit Set to find the correct rows/selected unit(s) for that specific chart, rather than assuming the master table applies to every chart. A table entry can hold more than one row — e.g. an organisation supporting two ICBs — which is expected, not a case to collapse. See Functional Spec, Section 10.4.

- **Master table** — whichever population table sits first in display order (`table_order[0]`). Drives the reporting unit picker and the batch loop. Position is the only definition of "master" — there is no separate flag, and reordering a table to position 0 makes it master with no further action. See Architecture, Section 5.

- **Population table** — a table sharing the common spine (`unit_id`, `unit_code`, `unit_name`, `soft_parents`, plus any number of `Name()` peer-group columns), e.g. `nhs_organisations`, a `submissions_{year}_{project_id}` table, or a `submissions_timeseries_{project_id}` table. A workfile can hold any number of them; see Master table for how one becomes the reporting-unit source. Built automatically the first time a chart pull encounters a project/year not already represented on the workfile — see Functional Spec, Section 7.2.

- **ReportContext** — the per-report identity object (`unit_id`, `unit_code`, `unit_name`), rebuilt fresh for each unit in a batch run and passed to text replacement. Not passed to Base Chart functions — Selected-unit identity there comes from the `"Selected"`-labelled `population_layers` entry instead. Carries no organisation identity of its own — an organisation, where the reporting unit's table has one, is reached via the Full Unit Set, not a field on `ReportContext`.

- **Soft parent (`soft_parents`)** — a relationship from one population table row to another, recorded on the child side only, as `table_name:id1^id2|table_name:id3`. Deliberately not called "parent": that word implies a strict one-parent-per-row structure, which these relationships don't have — a row may hold zero, one, or several ids in a given table, and may link to any number of different tables at once (e.g. an organisation supporting two ICBs). Resolution is one hop only, in both directions — see Full Unit Set. See Architecture, Section 5, for the format.

- **Unit / unit ID / unit code** — the identifier fields for a single row in a population table. `unit_id` is the internal identifier, stable within that table; `unit_code` is the outward-facing label (used for display only, never relied on for logic); `unit_name` is the display name (e.g. Trust name). See Population Tables, Functional Spec §7.2.

### Cluster 10 — Chart construction

- **Autotable** — a table populated from statistics computed by the shape modules (plus the value(s) for the selected unit(s)), read directly from the shapes on demand, rather than from text tag replacement. Draws on Summary stats (see Cluster 7) or on the shapes directly. Distinct from text-tag-based tables. Not yet built. See Functional Spec, Section 10.5.

- **Base Chart** — one of ChartGen's chart-rendering functions, each a standalone artefact handling one canonical data shape. See the Architecture document, Decision 18.

- **chart_inputs** — the fixed four-parameter call every Base Chart function receives: `population_layers`, `width`, `height`, `tweaks`. See Functional Spec, Section 10.0.

- **Custom Chart** — a Base Chart saved into a workfile rather than shipped with ChartGen, typically authored with an AI's help. Behaves identically to a built-in from the point it's saved. See Functional Spec, Section 10.9, and Architecture, Decision 18.

- **Reference id** — a short, stable id tag (e.g. `Mn`, `1Mna`, `P2a`) identifying one statistic in a Summary stats table, generated by `reference_rows_for_shape_type`. Scoped per shape type, not global — the same id means the same statistic in every table of that type. Deliberately short: intended to eventually serve as a literal PowerPoint table replacement tag, where a wider tag would change the table's own cell size. Stat-letter prefix (e.g. `Mn` = Mean); period number prefixed for TimeSeries; series letter suffixed only when a shape carries more than one metric-series, restarting at "a" per shape instance. See Functional Spec, Section 9.4, and Architecture, Decision 15.

- **Tweak** — the `tweaks` component of the chart_inputs contract (see chart_inputs) — a free-text Running Order column, uninterpreted by anything outside the Base Chart function it's passed to. No specific tweak behaviour is built yet — no Base Chart function reads the value. See Architecture, Decision 16.

### Cluster 11 — Excel integration

- **Driver range / export range** — Excel named ranges used by `insert_from_excel`: the driver range receives the current `unit_id`; the export range is the area captured as an image afterwards.
