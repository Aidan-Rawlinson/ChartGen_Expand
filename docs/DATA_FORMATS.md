# ChartGen - Data Formats

Every persisted and in-memory format. Verified against the code.

---

## The `.cgw` archive

A ZIP. `chartgen/workfile/state/workfile_file.py` is the only module that reads or writes it.

```
MyWorkfile.cgw
├── workfile_config/
│   ├── settings.csv
│   ├── tables/
│   │   └── {table_name}.csv
│   ├── running_order.csv
│   ├── text_stats.csv
│   ├── chart_store.csv
│   ├── custom_charts/
│   │   ├── custom_charts.csv
│   │   └── {shape_type}/{base_chart_name}.py
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

Index-plus-payload pairs, all following the same pattern as `manifest.csv` plus the cache files: an index CSV alongside one file per row.

| Index | Payload | Payload keyed by |
|---|---|---|
| `data_cache/manifest.csv` | `data_cache/{hex_id}.json` | `hex_id` |
| `custom_charts/custom_charts.csv` | `custom_charts/{shape_type}/{name}.py` | `base_chart_name` |
| `custom_tables/custom_tables.csv` | `custom_tables/{ref}.py` | `table_type_ref` |
| `output_tables/output_tables.csv` | `output_tables/{table_id}.csv` | `table_id` |

`template/MyWorkfile.pptx` is a reference copy for validation only and is never run from.

Flat, one-row-per-entity data is CSV. The cache files are JSON because a serialised data shape is nested. Cache files are never hand-edited.

---

## `workfile_info.json`

Stored `ZIP_STORED`, uncompressed, so it can be read by name before the rest of the archive loads.

| Key | Value |
|---|---|
| `workfile_name` | File name without the extension |
| `last_saved_by` | Username from the session that saved |
| `last_saved_at` | ISO datetime |
| `chartgen_version` | The `software_id` of the build that saved |
| `file_version_id` | The `.cgw` structure version, independent of `chartgen_version` |
| `locked_by` | Advisory lock holder, blank when unlocked |
| `locked_at` | ISO datetime the lock was written |

`locked_by` and `locked_at` are written on Open and cleared on Close. A Read-Only session writes neither and clears neither.

A `file_version_id` outside this build's readable list is refused at Open.

---

## `settings.csv`

Two columns, `key` and `value`. An open key-value store, not a fixed schema.

| Key | Holds |
|---|---|
| `description` | The workfile's "what is this for" text |
| `workfile_folder`, `outputs_folder` | Resolved paths |
| `ppt_template_path`, `cleaned_template_path` | Template paths |
| `table_order` | `\|`-delimited population table names. Position 0 is the master table |
| `template_page_width_emu`, `template_page_height_emu` | Page size, captured once at template processing |
| `selected_unit_id`, `reporting_unit_name` | Current reporting unit |
| `batch_cursor` | Position within a batch run |
| `next_stat_tag_id`, `next_table_id`, `next_chart_store_id` | Base-36 id counters, one per id space. Only ever advance |
| `charts_sheet_state`, `output_tables_sheet_state` | Sandbox control values as a JSON blob |

`settings.csv` holds no project identity. No year, no `project_id`, no project name. A workfile can span several projects, so none of those are workfile-level facts. Project identity lives on the manifest row and in the population table names.

---

## Population tables

`workfile_config/tables/{table_name}.csv`. Any number of them, added and removed freely. Examples: `nhs_organisations.csv`, `submissions_2026_123.csv`, `submissions_timeseries_456.csv`.

No fixed column schema at this layer. Each table is written from its own rows' keys. The spine below is a convention followed by whichever module builds the rows, not something `workfile_file` enforces.

`table_order` in `settings.csv` is the only record of order, and the only definition of "master" anywhere in the system. There is no master flag.

### Shared spine

| Column | Holds |
|---|---|
| `unit_id` | Stable internal identifier for the row, within this table |
| `unit_code` | Outward-facing label. Display only, never used for logic |
| `unit_name` | Display name |
| `soft_parents` | Relationship links to rows in other tables |
| any `Name()` column | Peer-group columns, for example `Region()`. Any number |

A table may add further `Name()` columns. It may not add other bespoke columns.

### `soft_parents` format

```
table_name:id1^id2|table_name:id3
```

`|` separates entries for different tables. `^` separates ids within one table. Recorded on the child side only; the table being linked to carries no reverse reference. A row may hold zero, one or several ids per table, and may link to any number of tables.

`shared/infrastructure/soft_parents.py` resolves one hop in either direction.

---

## Running Order

`workfile_config/running_order.csv` is the canonical store. The `.xlsx` is generated from it for export and parsed back on import, and is never written into the archive.

| Column | Holds |
|---|---|
| `row_id` | 1-based integer. Renumbers on insert, delete or reorder. Never a storage key |
| `enabled` | 1 or 0. Disabled rows are skipped |
| `scope` | `normal`, `batch_open` or `batch_close` |
| `function` | One of the Running Order function names listed below |
| `slide_index` | 0-based. Blank for structural functions |
| `base_chart_name` | Base Chart function name. Chart rows only |
| `cache_file` | Cache filename supplying this chart's data. Chart rows only |
| `table_id` | Output Table this row renders. Table rows only |
| `table_type_ref` | Base Table function name. Table rows only |
| `populations` | Per-row populations string. Blank inherits the default |
| `start_period` | Inclusive range start. TimeSeries only. Blank means from the first period |
| `end_period` | Inclusive range end. TimeSeries only. Blank means to the last period |
| `metric_periods` | `^`-delimited period value or values. TimeSeries only. Converts the row to a NumericSeries snapshot. Blank means no conversion |
| `image_path` | Source image for `insert_picture`. May contain `[code]` or `[id]` tokens, substituted by that function itself, separately from the Text Tag of the same name |
| `excel_path` | Workbook for `open_excel`, `insert_from_excel`, `close_excel` |
| `export_range` | Named range captured as an image |
| `driver_range` | Named range receiving the current `unit_id` |
| `left_emu`, `top_emu`, `width_emu`, `height_emu` | Position and size in EMU, populated from the template |
| `hyperlink_left`, `hyperlink_top` | `insert_chart` only, optional. EMU offset from the chart's top-right corner, not an absolute slide position |
| `hyperlink_size` | `insert_chart` only, optional. Square, in EMU. Blank defaults to 360000 |
| `hyperlink_colour` | `insert_chart` only, optional. Hex string. Blank defaults to `#0563C1` |
| `tweaks` | Free-text string, passed through uninterpreted. Blank is `""`, never `None` |
| `notes` | Free text, ignored at runtime |

A hyperlink icon is drawn only when both `hyperlink_left` and `hyperlink_top` are present. Blank in either means no icon. `0` is a present, valid value and is not the same as blank.

The functions: `create_ppt`, `set_default_populations`, `update_text`, `insert_chart`, `insert_table`, `insert_picture`, `insert_from_excel`, `open_excel`, `close_excel`, `empty_placeholder`, `save_ppt`, `save_pdf`.

---

## Manifest table

`data_cache/manifest.csv`. One row per chart URL. The canonical index of every chart in the workfile.

| Column | Holds |
|---|---|
| `chart_ref` | Display index, `Chart_0001` style. Renumbers across non-deleted rows on every add, delete or reimport. Blank on deleted rows. Never a storage key |
| `hex_id` | 5-digit uppercase hex. Stable for the row's lifetime, never reused, never renumbered. Names the row's cache file |
| `url` | The toolkit URL |
| `chart_title` | Taken from the fetched data shape |
| `database` | `nhs` or `indicators`. Resolved once at URL entry from the path shape. The source of truth thereafter |
| `project_id`, `service_id`, `year`, `shape_type` | Populated at fetch |
| `source` | `Template` for yellow-box extraction, `Direct Input` for user-entered |
| `deleted` | 1 or 0 |
| `added_at`, `data_updated_at` | ISO datetimes |

Fetch-populated cells hold the placeholder `...` until the first fetch.

A deleted row stays in the table with its `hex_id` reserved and its cached data kept. It is hidden from the UI, excluded from the Excel export, and skipped by fetch. A template re-upload containing its URL restores it under the same `hex_id`.

---

## Stat Tags

`workfile_config/text_stats.csv`. One row per tag, flat, no relational structure. Several tags sharing the same cut each repeat the fields independently.

| Column | Holds |
|---|---|
| `tag` | `T` plus a base-36 id, never reused. This is the literal `[tag]` text placed in a template. May be set by hand via the Excel round trip, in any form |
| `hex_id` | The manifest row this tag's data comes from |
| `populations` | A single population token, not a populations string |
| `start_period`, `end_period`, `metric_periods` | TimeSeries only |
| `reference_id` | Which reference id to read from the resolved population |
| `description` | Free text, ignored at resolution |

---

## Chart Store

`workfile_config/chart_store.csv`. Flat and unordered. No position field and no insert-relative-to concept.

Mirrors `CHART_SANDBOX_FIELDS` exactly, plus its own id and description.

| Column | Holds |
|---|---|
| `chart_store_id` | `C` plus a base-36 id, never reused. May be set by hand via the Excel round trip, in any form |
| `base_chart_name`, `cache_file`, `populations` | As the Running Order's own columns |
| `start_period`, `end_period`, `metric_periods` | TimeSeries only |
| `width_emu`, `height_emu`, `tweaks` | As the Running Order's own columns |
| `description` | Free text, user reference only |

A blank `populations` inherits the Running Order default.

---

## Output Tables

### Index

`workfile_config/output_tables/output_tables.csv`.

| Column | Holds |
|---|---|
| `table_id` | Base-36 id, never reused. Also written into the grid's corner cell, cosmetically. May be set by hand via the Excel round trip, in any form |
| `table_name` | User-typed for a manually created table, auto-generated `Table_1`, `Table_2` for a yellow-box one. Never used to match a re-uploaded template's box against an existing table |
| `rows` | Content row count N, excluding the header row |
| `columns` | Content column count M, excluding the header column |

### Grid

`workfile_config/output_tables/{table_id}.csv`. No fixed column schema; columns are named generically `c0` to `cM` via `grid_store.col_key`. An (N+1) by (M+1) grid.

| Cells | Hold |
|---|---|
| Row 0, col 0 | The table's own `table_id`. Display only, never read back |
| Row 0, cols 1 to M | Column widths, percent of total table width, 2 decimal places |
| Rows 1 to N, col 0 | Row heights, percent of total table height, 2 decimal places |
| Rows 1 to N, cols 1 to M | Content |

Widths and heights each sum to about 100%, validated on an explicit Update to a tolerance of plus or minus 0.5%, never auto-corrected.

A new table is `DEFAULT_TABLE_ROWS` by `DEFAULT_TABLE_COLUMNS`, currently 7 by 4, whatever created it.

### Cell content grammar

| Form | Means |
|---|---|
| plain text | Constant text |
| `[T3]` | A Stat Tag, resolved before the renderer sees it |
| `{C3}` | A Chart Store chart component, recognised and reported by the Base Table function itself |
| `<br>`, `<br/>`, `<br />` | A line break, converted to a real newline before the renderer sees it. Case-insensitive |

A chart component is recognised by a plain string check: starts `{`, ends `}`, first inner character is `C`. Nothing after that is checked, so hand-typed ids such as `{CH1}` are valid.

---

## Custom Charts and Custom Tables

| File | Columns |
|---|---|
| `custom_charts/custom_charts.csv` | `base_chart_name`, `shape_type`, `added_at`, `notes` |
| `custom_tables/custom_tables.csv` | `table_type_ref`, `added_at`, `notes` |

Custom Charts are filed under a folder per `shape_type`, mirroring the built-in Base Charts. Custom Tables sit flat, because a Base Table is not scoped to a data shape.

A `table_type_ref` must not collide with a built-in or with another Custom Table in the same workfile.

---

## Cache files

`data_cache/{hex_id}.json`, one per fetched chart, holding a serialised data shape. Roughly 50 to 100KB each, so a 200-chart workfile is under 20MB in memory.

`cache_writer.save_chart` serialises any shape generically. Reading is per shape: `cache_reader.py` has one `_from_dict_*` deserialiser per shape, dispatched through `DESERIALISE_MAP`.

Every shape carries:

| Field | Holds |
|---|---|
| `population_table` | The population table this chart's units belong to. Set once, at fetch |
| `population_label` | Set per layer by `build_population_layers`. `"All"`, `"Selected"`, or a resolved peer-group value |
| `metadata` | A dict travelling with the shape without being part of it. Currently `source_url`, default `None` |
| `format_modifier` | Display formatting for the shape's own values |
| `has_valid_unit_data` | Set on every shape. No consumer reads it |

A new shape-level field must be added explicitly to both `cache_reader.py`'s deserialisers and `shape_transforms.py`'s TimeSeries to NumericSeries conversion, or it silently resets to its default on every pass.

### PairedSurveyData

| Structure | Holds |
|---|---|
| `PairedObservation` | `patient_label`, `start_value`, `end_value` |
| `PairedSurveyDataUnit` | A `records` list, in place of `values` or `response` |
| `PairedSurveyDataStats` | `count_with_data`, `count_null`, `mean_start`, `mean_end`. No median, quartiles, min or max |

A record counts toward `count_with_data` if either start or end is present.

Flat shape-level `units` list, no `metrics` wrapper: always exactly one Metric-Series.

`patient_label` is a positional label, "Patient 1", with no meaning beyond distinguishing rows. Not identifiable and not pseudonymised patient data.

---

## Reference ids

`shapes/reference_ids.py` converts a shape's summary stats into short, PowerPoint-tag-safe rows of `{"id", "label", "kind", "value"}`, one converter per shape type.

Scope is per shape type, not global. `Mn` means the same statistic in every NumericSeries table.

| Shape | Fixed part |
|---|---|
| NumericSeries | `C`, `Nd`, `Mn`, `Md`, `Q1`, `Q3`, `Mi`, `Ma` |
| TimeSeries | The same letters, prefixed by a 1-based period number in `shape.periods` order |
| CategoricalCompositional | `C` or `Nr`, then a 1-based running number per category, each with a `P`-prefixed percentage twin |
| NumericCompositional | `T`, then a 1-based running number per component, each with a `P`-prefixed percentage twin |

A series letter, `a`, `b`, `c` and so on, is appended last, and only when the shape carries more than one metric-series. It restarts at `a` for each shape instance.

`kind` governs display, not calculation.

| `kind` | Display |
|---|---|
| `value` | Respects the shape's `format_modifier` |
| `count` | Always a plain integer |
| `percent` | Always a percentage, regardless of `format_modifier` |

PairedSurveyData has no converter and does not participate in Stat Tags.

---

## Alongside the `.cgw`

```
MyWorkfile.pptx
CG_Extracts/
outputs/
├── pptx/
└── pdf/
```

| Path | Holds |
|---|---|
| `MyWorkfile.pptx` | The cleaned template. User-owned, directly editable. ChartGen always runs from this |
| `CG_Extracts/` | Every Excel round-trip file. Created on first use |
| `outputs/pptx/`, `outputs/pdf/` | Generated reports. Created on first run, wherever the `.cgw` currently lives. Not carried across a Save As |

`CG_Extracts` filenames: `{workfile_name}_chart_urls.xlsx`, `running_order.xlsx`, `chart_store.xlsx`, `stat_tags.xlsx`, `{table_id}_grid.xlsx`, `{table_name}.xlsx`.

The Custom Charts and Custom Tables bundle downloads are not Excel round-trips and do not go here.

---

## In memory

Only `WorkfileState` holds real state. Everything else is rebuilt from it on every run.

```
st.session_state
├── ["ws"] -> WorkfileState
├── ["token"]
├── [tab-prefixed UI keys]
└── per-batch-run objects
    ├── AssemblyContext
    ├── ReportContext
    └── list[data shape]
```

### `WorkfileState`

| Field | Mirrors |
|---|---|
| `workfile_path`, `workfile_name` | File identity |
| `settings: dict` | `settings.csv` |
| `tables: dict` | `tables/*.csv`, keyed by table name |
| `table_order: list` | The `table_order` setting. Position 0 is the master table |
| `running_order_rows: list` | `running_order.csv` |
| `manifest_rows: list` | `manifest.csv` |
| `cache: dict` | `{hex_id}.json`, keyed by filename, values are JSON strings |
| `custom_chart_rows` / `custom_chart_code` | The `custom_charts/` index and payload, code keyed by `base_chart_name` |
| `custom_table_rows` / `custom_table_code` | The `custom_tables/` index and payload, code keyed by `table_type_ref` |
| `text_stats_rows: list` | `text_stats.csv` |
| `chart_store_rows: list` | `chart_store.csv` |
| `output_table_rows` / `output_tables` | The `output_tables/` index and one grid per `table_id` |
| `template_pptx_bytes` | The reference template copy |
| `last_saved_by`, `last_saved_at`, `locked_by`, `locked_at`, `file_version_id` | `workfile_info.json` |
| `dirty: bool` | Session only, not persisted |
| `read_only: bool` | Session only. True for a session opened Read-Only, which never holds the lock |

### `AssemblyContext`

One per batch, persisting across the reports in it.

| Field | Holds |
|---|---|
| `prs` | The open `Presentation` |
| `output_path`, `template_path` | Paths for this report |
| `log: list[dict]` | Per-row run log. No consumer reads the full list |
| `report_context` | Rebuilt per report |
| `full_unit_set: dict` | Rebuilt per report. The reporting unit's own row plus every row one hop out via `soft_parents`, keyed by table name |
| `default_populations: str` | Set by a `set_default_populations` row |
| `excel_workbooks: dict` | Attached dynamically by `open_excel`, not declared on the class |

`insert_chart` looks a data shape's own `population_table` up in `full_unit_set` rather than assuming the master table applies to every chart.

### `ReportContext`

One per report, rebuilt fresh per unit from the per-report settings dict. Holds `unit_id`, `unit_code`, `unit_name` and nothing else. Organisation identity, where the reporting unit's table has one, is reached through `full_unit_set`.

### Population-filtered shape lists

One list per `insert_chart` call, built fresh by `build_population_layers`. Each entry is a filtered copy of the chart's data shape with its stats recalculated.

---

## Conventions

**Base-36 ids** come from `shared/infrastructure/id_generation.py`, from a persisted counter per id space. Never recomputed from surviving rows, never reused.

An id can also be typed by a person, in any form, through the Excel round trip each of these tables has. So a system-issued id is checked against the ids already in use rather than inferred from the counter: `next_unique_id` skips any candidate already taken, comparing case-insensitively and parsing nothing. Rules and rationale in `shared/infrastructure/CLAUDE.md`.

| Prefix | Id space |
|---|---|
| `T` | Stat Tag |
| `C` | Chart Store entry |
| none | Output Table |

The `T` and `C` prefixes exist so both can appear unambiguously in the same Output Table cell grammar.

**Delimiters.** `|` separates entries for different tables in `soft_parents` and separates table names in `table_order`. `^` separates ids within one table in `soft_parents`, separates tokens in a populations string, and separates values in `metric_periods`.

**Period fields are stored verbatim.** `start_period`, `end_period` and `metric_periods` hold exactly what the user picked or typed, typically `period_label(period_id)`. The xlsx writer and reader are pure passthrough. Numeric extraction happens only in `cut_resolution.prepare_chart_cut`.

Each Indicators report has its own independent period numbering. The same calendar month can be a different `period_id` in two reports. There is no cross-report period-id space.

An unresolvable `metric_periods` id is a no-data case: its own output metric, every value `None`, labelled with the bare id in parentheses.

**EMU is the only sizing unit** in every stored format and every render call. Percent exists only inside the two Sizing widgets.

**Excel percentages** are read through `cell.number_format` as well as `cell.value`. Excel stores a typed `5%` as the float `0.05` with a percentage format, so a format containing `%` means multiply back up by 100, round, and append `%`. Currently done in `grid_xlsx.py` only.

**Excel round-trips are full-replace**, except the manifest table. A row absent from an imported Running Order, Stat Tags, Chart Store or Output Table grid file is gone. A row read back with a blank id is issued a fresh one. The manifest table alone merges on `hex_id` identity with a soft-delete flag.
