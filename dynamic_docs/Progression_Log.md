<!-- Purpose: A session-by-session history of what was built and what was decided. The project record. Authored by Claude at session level, not micro-decision level. -->

## Session: Installer, update mechanism, and versioning

Built the full installer and update feature end to end, from initial planning through to a real compiled installer tested on the user's machine.

Covered in order: confirmed the install-location decision (%LOCALAPPDATA%, no admin rights), built the file version compatibility mechanism (a new software id / file version id distinction, with a hard refuse at Open on incompatible file versions), built optional double-click-open (reusing the existing Open Workfile flow rather than a separate silent-open path), and built the Check for Update mechanism (manual button only, OneDrive-for-Business path resolution, PE metadata version comparison, no automatic or background checking).

Designed both icon assets collaboratively with the user through many iterative rounds (colour palette matched against a reference image the user supplied, chart-and-slider composition, ascending bar heights, dot placement), then rasterised them into real multi-resolution .ico files using PIL in the sandboxed environment (no SVG renderer was available, so shapes were redrawn programmatically rather than converted directly from the SVG source).

Wrote the Inno Setup script (installer/ChartGen.iss): fixed AppId, .cgw file association under HKCU, both icons, venv cleanup on uninstall. User installed Inno Setup 7 and compiled it successfully on the first attempt. User then tested the installer, confirmed the .cgw icon, confirmed double-click-open, and copied the real installer to the actual SharePoint release location (replacing the placeholder file that had been used for earlier path-resolution testing).

Updated project documentation: Functional Spec Section 5 restructured into 5.1 (File Version Compatibility, new) and 5.2 (Concurrency, existing content unchanged), per the user's explicit steer to keep this behaviour in one document rather than split between Architecture and Functional Spec. Added matching Glossary terms and a Feature List row, and corrected two Feature List rows that had gone stale (file association and custom icon, previously marked "Not built, requires an installer"). Wrote a new standalone user_resources/Installer_Guide.md covering the whole feature, the release checklist, and install/uninstall steps.

Consolidated a duplication found along the way: workfile_file.py had its own separate CHARTGEN_VERSION constant, now replaced with a reference to the single version_compatibility.csv source of truth.


## Session: Expansion planning and Step 1 — the manifest table

Opened by deleting the stale Architecture Decision 9 (application location) — obsolete now the installer exists and the situation is nuanced.

Planned the multi-project / multi-database expansion with the user: reviewed the intended shift (one .cgw no longer tied to one project/year; just-in-time credentials; URL triage by database; submissions vs organisations split), and agreed a seven-step development plan, now recorded in Current_State.md. Marked the project phase explicitly as Expansion in Current_State.md, with a standing instruction block for future Claude sessions.

Built Step 1 end to end — the manifest table:

- Designed the schema with the user: chart_ref (display index, renumbering), hex_id (stable 5-digit hex identity, names the cache file), url, chart_title, database, project/service/year, shape_type, source (Template / Direct Input), deleted flag, added/updated timestamps, `...` placeholders pre-fetch.
- Consolidated three overlapping stores into one: workfile_config/urls.csv and data_cache/manifest.json both deleted, replaced by data_cache/manifest.csv as single source of truth. Cache files renamed {hex_id}.json. File version and software id bumped to 0.0.2; 0.0.1 workfiles hard-refuse.
- Decoupled fetching from template processing: extraction populates the table and generates the Running Order immediately (cache_file assignable pre-fetch thanks to hex_id); the Imports tab's Fetch button is the single fetch, a full refresh updating each row's fetch-populated columns.
- New package core/acquisition/manifest_table/ for the Excel round-trip (formatted export with 300 blank input rows; import semantics: blank hex_id = new Direct Input row, missing hex_id = deleted with data retained, unknown hex_id rejected, template re-upload resurrects deleted URLs under their original identity).
- Reworked the Imports tab: read-only table display, Excel-only editing (an in-table editor was built, then removed at the user's request after live testing), upload behind a toggle button matching the Running Order tab's pattern.
- Verified with sandbox compile checks and functional tests of the merge/import semantics; user live-tested end to end including output generation. One mid-test failure (Running Order referencing old-style cache names) was diagnosed as a stale hot-reloaded process, resolved by relaunch and template re-process.

Dead-code sweep after the build: removed the unused label parameter from parse_url, removed the unused SYSTEM_COLUMNS constant, fixed a stale comment in generation.py.

Updated all four affected governed documents (Architecture, Functional Spec, Feature List, Glossary) per the agreed proposals; mirror copies written mid-session and re-uploaded to Project Files by the user at Close-down.


## Session: Multi-project population tables, chart-population resolution, and New Workfile streamlining

Built Step 2 (multi-project, same database) and Step 6 (streamlined New Workfile flow) of the seven-step expansion plan end to end, plus a full documentation catch-up (Step 7). Steps 3–5 (second database) remain untouched.

**Multi-table population model.** Replaced the single `units.csv`/`WorkfileState.units` with a generalised `tables`/`table_order` model — any number of named population tables, one CSV each inside `.cgw` (`workfile_config/tables/{table_name}.csv`), `table_order` recorded in `settings.csv`. File version bumped 0.0.2 → 0.0.3; older workfiles hard-refuse, per the existing no-migration convention. Built `nhs_organisations` and `submissions_{year}_{project_id}`, both on a shared spine agreed with the user through extensive discussion: `unit_id`, `unit_code`, `unit_name`, `soft_parents`, plus any number of `Name()` peer-group columns — every population table carries identical headers, no bespoke columns. `nhs_organisations` filtered to organisations actually referenced by a submission, not every organisation for the year.

**`soft_parents` relationship model.** Worked through with the user from first principles: relationships between population tables are not always singular ("parent" was explicitly rejected as a term — risks biasing toward single-value assumptions in code and conversation, per the user's direct question about whether the word itself would cause problems for Claude). Landed on "soft_parents" — recorded on the child side only, delimiter-based (`table:id^id|table:id`), generalising to one-to-many, multiple-independent-links, and many-to-many all at once. Built as a shared module (`core/shared/infrastructure/soft_parents.py`): `format_soft_parents`, `parse_soft_parents`, `resolve_related_rows` (forward), `resolve_referencing_rows` (reverse — needed once the user pointed out resolution has to work in both directions, not just child-to-parent), `resolve_all_related_rows`, `resolve_full_unit_set` (a row's own table plus everything one hop out, the basis for both the Select tab's Full Unit(s) display and chart population resolution). Deliberately one hop only — flagged repeatedly as a scope boundary, not a limitation to silently work around.

**Master table.** Whichever population table sits first in `table_order` is master — position is the only definition, no separate flag, confirmed explicitly with the user. New Populations tab built (reorderable ▲/▼, collapsible, starts collapsed, ★ MASTER badge) after `soft_parents` display iterated through several rounds of font-size/colour/spacing feedback. Select tab trimmed to just the reporting-unit picker plus Full Unit(s), renamed "Reporting unit selection".

**Chart-population resolution — the harder half.** Added `population_table` to all three data shapes, stamped at fetch time from the chart's own URL (`fetch.py`), not derived from the workfile's current master table. Reworked `insert_chart` (and the Charts tab preview) to resolve each chart's own table and correct `Selected` unit(s) via a new `AssemblyContext.full_unit_set`, built once per report. Corrected an initial misunderstanding along the way: `Selected` resolving to *more than one unit* (e.g. an organisation with several submissions, or one organisation supporting two ICBs) is intended behaviour, not an edge case to collapse — `population_layers.py`'s existing set-based `Selected` resolution already supported this once `selected_ids` was passed as a set rather than derived from a single `ReportContext.unit_id`. `ReportContext` correspondingly lost its `organisation_id`/`organisation_name` fields.

**Automatic population-table creation.** Originally scoped as a user-facing "Add Project" feature; the user redirected this to be fully automatic instead — `ensure_population_tables` triggers inside `fetch.py`, per chart, the moment an unseen project/year combination is identified from the chart's own URL, with no user-facing step at all. This required relocating `add_project_tables`/`build_organisations_table`/`build_submissions_table` out of `workfile.setup.new_workfile` into `acquisition.toolkit_nhs.population_tables` — acquisition code must not depend on `workfile.setup` (one-way dependency rule), and this logic used to sit on the wrong side of that boundary. `add_project_tables` merges `nhs_organisations` across projects (append by `unit_id`, existing rows untouched) rather than rebuilding it from scratch, per explicit agreement that `Region()` needs no re-processing since it's a per-organisation API value, not a cross-table computation.

**New Workfile flow streamlined.** Year/project/name entry replaced with a short description field (free text, "what is this workfile for" — shown next to "ChartGen" in the app header, Coral Red `#FF4B4B`, purely for the person) and a single native Save dialog (`pick_save_file`, added to `pickers.py`) for both New Workfile and Save As — replacing the old folder-picker-plus-textbox pattern and the app's own overwrite-confirmation step (the OS dialog already handles it). `create_new_workfile` now has zero knowledge that projects or population tables exist; year/project_id/project_name are no longer stored at the workfile-settings level at all, on the explicit basis that none of them are workfile-level facts once one workfile can hold more than one project.

**Other fixes and additions along the way:** chart titles removed from all 17 Base Charts; the bead-string plot's tiers de-duplicate visually (a unit already shown in a more specific tier is suppressed from broader ones — statistics unaffected); a real bug found and fixed where the Populations tab showed stale data after Fetch (fixed by adding the missing `st.rerun()`, matching the existing flash-message pattern used elsewhere); Charts tab wired to read the Running Order's live `set_default_populations` value (flagged throughout as a stopgap).

**Documentation.** Scrubbed the "Refactoring Issues" concept from the Docs Maintenance Guide entirely, at the user's explicit instruction — this phase is new functionality, not refactoring, and the framing shouldn't imply otherwise. The Guide now governs five documents, not six; deferred/known gaps route to Feature List Notes instead. All five governed documents (Guide, Feature List, Architecture, Functional Spec, Glossary) brought current against the actual code; Primer untouched throughout (edit-locked, no request made to change it). Mirror copies written mid-session throughout, per Section 8 of the Guide.


## Session — Second Toolkit (Indicators) and Credentials Relocation

**Credentials moved to Config tab.** Removed the app-level login gate entirely (`require_authentication`/`_render_login` in `login_form.py` replaced with `render_credentials_box`, called from `config_tab.py`). No login required to launch, create, open, or save a workfile — Fetch fails soft with none validated. Confirmed via real VBA (`GetToken`) that one shared credential set/token authorises both the NHS and Indicators APIs, so this is a single box, not per-database. Save-attribution call sites (`new_workfile_form.py`, `open_workfile_form.py`, `save_as_form.py`, `sidebar.py`) changed from `st.session_state["username"]` to `.get("username", "")` per user decision (blank, not OS-username fallback).

**New canonical shape — TimeSeries.** Built from a real Indicators toolkit VBA export (`GetInfo`/`GetReportInfo`/`GetDataInfo`/`GetVisibleDates` against `icsapi.nhsbenchmarking.nhs.uk`). Period axis lives once on the shape, not per metric, per explicit user correction ("a data shape relates to a single dataset"). API-supplied period stats (`dateAverages`/`dateMedians`/`calculatedNationalAverages`) dropped entirely — stats recomputed locally per period, matching every other shape's convention. Visible-dates filtering (`outputAvailability <= today`) and the VBA's own untrusted-but-relied-on period ordering both mirrored exactly, per user instruction not to second-guess it.

**New package — `core/acquisition/toolkit_indicators/`**, mirroring `toolkit_nhs/`'s shape: `api_client.py`, `url_parser.py`, `table_naming.py`, `population_tables.py`, `transformers.py`, `fetch.py`. URL shape confirmed against real examples (`members.nhsbenchmarking.nhs.uk/project/{id}/toolkit`); tier-id extraction cascade (`o`→`d`→`c`→`b`) and the "no `date=`" graceful fallback both mirror the source VBA exactly, including a discrepancy in the real URLs supplied (missing `=` after `date` in several examples) — not corrected, matched to existing VBA fallback behaviour instead.

**New population-table trigger model.** `submissions_timeseries_{project_id}` merges on every fetch (not build-once like NHS's `ensure_population_tables`) — a single report response spans a project's full period history, and submissions genuinely drop in/out over time (confirmed by user). `Region()` is carried on these rows too, sourced from `nhs_organisations` at merge time rather than left blank — corrected mid-session after the user pointed out Region() was never chart-data-derived on the NHS side either.

**Deliberate deviation from VBA, flagged and accepted:** `GetVisibleDates`'s hardcoded project `42` not replicated — the parsed `project_id` is used instead, consistent with the naming convention already being project-generic.

**Deliberately skipped:** the VBA's `GetInfo`/tiers endpoint — its only extracted value (`TierName`) is unused elsewhere in the source code.

**`cache_writer.py` moved** from `toolkit_nhs/` to `shared/infrastructure/` — audited as having no NHS-specific logic, now shared rather than duplicated per toolkit package.

**`core/acquisition/url_triage.py` and `core/acquisition/fetch_dispatch.py`** — new, sit outside both toolkit packages. Triage by path shape (`/outputs/{id}` vs `/project/{id}/toolkit`), confirmed against real URL examples from both sources. Fetch dispatch originally shipped with two separate progress-bar phases (NHS then Indicators); corrected on request to report one continuous total across both.

**Organisation ID collision** — resolved by explicit user decision to assume shared identity space between the two APIs "for the moment," revisit if it breaks.

**Correction, own error:** initially told the user `format_modifier` was unpopulated across all three existing shapes. Checked against actual code before documentation: NumericSeries and NumericCompositional already populate it correctly; only CategoricalCompositional lacks it. Corrected in Current_State/Next_Session and in the TimeSeries module's own docstring.

**Chart rendering for TimeSeries explicitly deferred** to next session, per user instruction — this session's scope ends at data landing in cache, confirmed via the Charts tab (identifies the shape, shows "no charts defined", doesn't crash).

**Docs:** All five governed documents updated to match (see Current_State for the full breakdown). Two prior sessions' documentation debt (credentials-tab wording, "three" vs "four" canonical shapes) closed out in the same pass as this session's own changes.


## Session — TimeSeries charting, Primer maturity statement, organisation-identity mismatch surfaced

Reviewed the existing chart pathway for the three built shapes (NumericSeries, NumericCompositional, CategoricalCompositional) end-to-end before touching TimeSeries, to keep the new path as close to identical as possible. Confirmed most of the pipeline (`insert_chart`, `build_population_layers`, EMU sizing, image insertion, Charts tab preview) was already shape-agnostic.

Wired TimeSeries into the two remaining generic dispatch points (`shapes/dispatch.py`, `population_layers.py`'s `_get_shape_units`) — both trivial, since `filter_time_series`/`time_series_autotable_stats` already existed from the previous session and just weren't called yet.

Built three Base Chart functions for TimeSeries in a new `base_charts/timeseries.py`: `period_line_chart` (mean + IQR band), then, at the user's request, `median_comparison_linechart` (median per layer, actual value(s) for Selected) and `full_lines_linechart` (full population as light grey lines, highlighted layers on top). Before wiring the last two into the registry, the user asked for a design pass — web research on spaghetti-plot/line-highlighting conventions confirmed the grey-background approach but flagged that flat light-grey with no transparency doesn't get the density effect real spaghetti plots rely on; fixed with thin lines + alpha. Also fixed a legend-duplication bug (per-unit labels inside a loop) using a proxy-artist pattern, applied to both new charts. All three then registered in `registry.py` and `chart_type_map.csv`.

Resolved the long-standing maturity-statement gap: drafted and, with explicit user approval, added a one-sentence anchor to the top of Primer Section 1 (Primer being edit-locked otherwise).

All three affected governed documents (Feature List, Functional Spec, Architecture) updated to match, written to the mirror mid-session per Section 8 of the Maintenance Guide.

Used `conversation_search` at the user's request to pull design intent from an earlier session (the Indicators org name/code extraction plan) when investigating a data-quality bug the user had spotted: `nhs_organisations` rows added via the Indicators toolkit were showing only `unit_id`, not name/code. Traced this to `population_tables.py`'s `extract_submissions` using field names (`organisationCode`, `organisationName`) that — unlike every other field it reads — are never used or confirmed anywhere else in the codebase, and noted the NHS toolkit's own equivalent uses `nhsCode`, not `organisationCode`, as a further hint the guessed key is probably wrong.

While discussing this, the user raised a much bigger concern: organisation IDs may not match between the NHS and Indicators APIs at all, which would mean the current `soft_parents` linkage is wrong at the root, not just missing display fields. User confirmed a lookup table will likely be needed, and gave explicit instruction that it must be applied at the earliest point in the pipeline (before the `soft_parents` link is formed), not patched on afterward. This was deliberately not built this session — user wants to draw up a full list next time rather than fix in isolation. Also discussed, at the user's prompting, whether anything in either API hints at the underlying database/system identity — no explicit field exists, but the differing hostnames (`icsapi` vs `membersapi`) were noted as a reasonable signal of separate backend systems, alongside an observation that `project_id` (unlike `organisation_id`) does appear to be a shared concept across both toolkit front-ends.

User also explicitly asked that the installer release status (an open item from a previous session) not be raised again for now, since the project is still solo/early-stage.


---

## Session — Charts Sheet / Running Order Two-Way Sync

Rebuilt the Charts tab from a preview-only stopgap into a full two-way sync with the Running Order: load an existing `insert_chart` row or a cached dataset directly, edit chart-relevant fields (chart type, data, populations, size), and write back via Overwrite / Insert above / Insert below. Round-trip governed by a single maintained field list (`CHART_SANDBOX_FIELDS`). Sizing moved to a percent-of-page-shorter-dimension unit, backed by a new page-size capture at template processing and a new `page_sizing.py` module. New `row_ops.py` module for generic row insert/overwrite, used by the save-back control. Rows referenced by `row_id` rather than position/label for stability across edits.

Extensive front-end iteration followed (Streamlit-native layout: expanders, columns, placeholder text, sizing tweaks) — no CSS used throughout, per explicit instruction. Found and fixed a genuine Streamlit bug along the way: a `None`-based "no selection" sentinel, once pre-set into `session_state` before widget creation, triggers Streamlit's own built-in placeholder text instead of a custom `format_func` — fixed by using plain string sentinels as real dropdown options instead.

Governed docs updated to match (Functional Spec §9.3/§9.4, Architecture package tree + Decision 11, Feature List, Glossary) — Primer untouched, edit-locked, not needed this session.

Organisation-identity mismatch work (flagged last session) remains parked — user now has a CSV extract ready to bring into next session to resolve it.


---

## Session — Organisation identity resolution (Indicators ↔ NHS)

Resolved the long-parked organisation-identity mismatch between the Indicators (ics) and NHS toolkits, confirmed real and fixed against live data this session.

**First pass (built, then retired):** the user supplied a one-off DB extract (`ics_org_table.csv`, ~1450 rows, columns including `organisation_id`/`external_organisation_id`) mapping ics organisation ids to nhs unit ids. Built `core/acquisition/toolkit_indicators/org_lookup.py` plus a static `static_config/ics_org_lookup.csv` copy, wired into `population_tables.merge_timeseries_population` as a translation step before the `soft_parents` link is written.

**Discovery mid-session:** while testing, found that `/projects/{id}/submissions` — the same endpoint `get_visible_dates` already called for `projectDates` — also returns `userOrganisations`: live `organisationId → externalOrganisationId` pairs per project, plus each organisation's `submissionList` carrying the real `submissionName` per `submissionId`. Confirmed via a live Network-tab capture from the user (project 42, MHLDA Indicators), including a multi-submission organisation (Central and North West London NHS FT, ics org 1043 → external 141).

**Decision:** on the user's explicit instruction, retired the static CSV approach entirely in favour of the live per-project data. Deleted `org_lookup.py` and `static_config/ics_org_lookup.csv` (plus the resulting stale `.pyc`); confirmed no dangling references anywhere in the codebase via full-repo search.

**Final mechanism:**
- `api_client.get_visible_dates` renamed to `get_project_submissions_data`, now returns the full response dict rather than just `projectDates`.
- `fetch.py` builds `org_id_map` (`{ics org_id: nhs unit_id or None}`) and `submission_name_map` (`{submissionId: submissionName}`) once per project per fetch run from that response, passing both into `merge_timeseries_population`.
- `population_tables.merge_timeseries_population` resolves each submission's organisation via `org_id_map`; a miss leaves `soft_parents` empty and `Region()` blank for that submission (minimum footprint, no invented value) and sets a `had_unmapped` flag.
- A newly-resolved organisation not yet in `nhs_organisations` is enriched via `toolkit_nhs.api_client.get_organisations`, queried against the current calendar year (confirmed with the user as the correct stand-in, since Indicators data has no year of its own) — pulls canonical `organisation_name`/`nhs_code`/`region_name`. Falls back to the Indicators response's own (incomplete) values only if the organisation isn't present in that year's NHS list.
- Submission `Region()` is resolved from this same now-enriched org data within the same pass, so a submission whose org is newly discovered this fetch gets the correct `Region()` immediately.
- `unit_name` now sourced from `submission_name_map`'s real `submissionName` (previously duplicated `anon_submission_code` into both `unit_code` and `unit_name` — a genuine bug, now fixed). `unit_code` remains `anon_submission_code`.
- `fetch.py` accumulates one `any_unmapped_org` flag across the whole run and appends a single synthetic `"warning"`-status entry to its results (message text, no per-submission detail) rather than warning per submission. `imports_tab.py`'s flash-message loop updated to render `"warning"` status distinctly from `"ok"`/`"error"`.

**Verified:** confirmed working end-to-end via a clean test run against a fresh workfile (first-time table creation for that project). The run also surfaced a real data-quality issue in the underlying ics database — some submissions have no matching organisation at all — correctly caught by the new unmapped-organisation warning. Confirmed as a database gap, not a ChartGen bug; user will investigate separately.

**Docs updated:** Functional Spec §7.4 (project-level call description; organisation-link/enrichment/naming paragraph rewritten). Architecture: module table row for `toolkit_indicators/` (mentions reuse of `get_organisations`); Decision 10's "Organisation identity assumption" subsection rewritten as "Organisation identity resolution," describing the live mapping mechanism in place of the earlier unverified assumption.

**Handoff:** user requested two items for next session — "an easy update on the population tables" and "the transformation that creates a metric data shape from a line chart data shape" — neither scoped in detail yet; see Next_Session.md.
