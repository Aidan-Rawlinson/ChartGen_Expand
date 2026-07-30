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

---

## Session — TimeSeries period handling + population-table Excel round-trip

**Population tables — Excel round-trip.** Added per-table download/upload (`core/shared/infrastructure/population_table_xlsx.py`), controls placed inside each table's "Show rows" expander on the Populations tab. Identity is `unit_id`: matched row updated, unmatched non-blank id added, blank id skipped, existing row missing from the file removed (no soft-delete flag on these tables). No validation of edited values — dangling `soft_parents` explicitly accepted as a known gap, deferred to a future table-wide validation pass at the user's request.

**Period Range (TimeSeries).** New Running Order columns `start_period`/`end_period` (period_id, blank = full range). `shapes/dispatch.py::apply_period_range` trims the period axis ahead of population-layer filtering — pure slice, no stats recompute (each period's stats are already independent). Charts sheet "Period Range" box (two selects, period labels only, never raw ids). Start-after-end or unresolvable id → empty range (not an error).

**Convert Periods to Metrics.** New `core/shared/normalisation_containers/shape_transforms.py::time_series_to_numeric_series()` — converts one or more periods into a NumericSeries snapshot, one output metric per (source Metric-Series × selected period), metric-major, `"MetricName (PeriodLabel)"` naming, chronological within each metric. Unresolvable period_id here is a hard error (row halts) — different from Period Range's silent-empty behaviour, per explicit user decision. New Running Order column `metric_periods` (`^`-delimited ids). Charts sheet "Convert to Metrics" multiselect. `get_valid_chart_refs_for_cache_file` gained a `converts_to_metrics` flag, threaded through everywhere the chart-type dropdown appears (xlsx writer, Running Order edit dialog, Charts sheet) so valid chart types switch to NumericSeries's when `metric_periods` is set.

**Running Order xlsx — hidden-sheet period dropdowns.** `start_period`/`end_period`/`metric_periods` validate against a hidden `_period_lists` sheet (one column per distinct cache_file, built once, shared across all rows referencing it), replacing Excel's 255-char inline-list limit. Cells display `period_label(period_id)`; reader extracts the id. `metric_periods` reuses the single-value dropdown but the cell can still hold a `^`-delimited multi-value string.

**Built then explicitly removed:** a chart-type reconciliation check on Excel upload (`clear_invalid_chart_types`) — user wants proper table-wide validation later instead, not a partial check now. Fully removed, no trace left.

**Docs:** Feature List, Functional Spec, Architecture, Glossary all updated to match (new Decision 12 in Architecture covers the period-handling work as a set). Primer untouched (edit-locked).

**Non-code:** established `st.tabs()` mechanics (no rerun on tab click, active tab never reaches `session_state`) in response to a "guidance PDF per current tab" sidebar idea. Three implementation options discussed, none chosen; nothing built.


## Session — Quick wins, login rebuild, tab consolidation, sidebar polish

Large mixed session working through a "quick wins" list plus follow-on UI work.

**Built/fixed:**
- `format_modifier` retrofit for `CategoricalCompositional` (was the one shape missing it), plus a full Excel-style number-formatting rule (`#,###` / `#,##0%` / `£#,##0`) applied consistently across all base charts via new `_format_number`/`_axis_formatter` helpers in `shared.py`. Replaced NumericSeries's old K-abbreviation formatter and NumericCompositional/TimeSeries's old "P"-only checks.
- Placeholder handling in `template_reader.py`: fixed a real bug (native Text placeholders were wrongly eligible for yellow-box matching — should only ever get tag-replacement text), and matched placeholders are now removed from the cleaned template alongside their yellow box (previously only the yellow box was stripped, leaving an empty placeholder behind).
- Verified the `organisationCode`/`organisationName` guessed keys in `extract_submissions` against live output — behaving as expected, gap closed.
- Login process rebuilt: mandatory sign-in gate (`render_login_gate`) at the very top of `app.py`, blocking everything until a valid token exists, replacing the old on-demand Config-tab validation. Found and documented a real side-benefit: this also closes a gap where an unvalidated session could silently defeat the advisory workfile lock via a blank username.
- Removed the Details tab and Config tab entirely. Details' content moved to a collapsed "Workfile Details" sidebar expander; Config's reference-CSV placeholder scope dropped (superseded by an API endpoint, no longer needed) and its credentials content moved to the gate.
- Added per-tab guidance links (`core/ui/common/guidance.py`) — small muted inline link after each tab's title, linking out to a per-tab URL. Sidesteps `st.tabs()`'s inability to report the active tab, since each tab renders its own link.
- Sidebar layout iteration: button groups, spacing, and a CSS pass (`layout_css.py`) targeting Streamlit's default padding/gaps. A cosmetic divider-line idea was tried extensively and dropped by explicit user call after consistent, unexplained CSS behaviour (see Current_State/Next_Session for details) — settled on plain spacer divs instead.

**Governed docs updated:** Functional Spec, Architecture, Glossary, Feature List — all reflecting the login gate, tab removals, placeholder-handling fix, and the number-formatting rule. Primer untouched. Net effect was a shorter set of docs overall (two tab-table rows removed outweighed additions).

**Not done / carried forward:** guidance URLs are still placeholders; no live batch-run test for anything built this session or last; table-wide Excel validation still deferred; Tweaks still not built. Full detail in Current_State.md and Next_Session.md.

## Session — Prototype-sharing prep (guidance content and links)

Scoped what's needed to hand a working ChartGen prototype to a colleague shortly: real per-tab guidance content, a quick-start guide, sample PowerPoint templates, and an installer check. Agreed no functional changes at this stage, and no known-issues briefing — this is a look/feel/usability prototype, not an alpha or beta.

Drafted succinct purpose/functionality write-ups for the sidebar and all seven tabs, then expanded them substantially by reading the actual tab source files (`core/ui/tabs/*.py`, `core/ui/workfile/*.py`) and cross-referencing the Functional Spec/Glossary — covering buttons and controls not previously referenced anywhere (Open Workfile's lock-decision states, the Charts tab's full control set, Outputs' preflight checks, etc.), and expanding the Text tab from a one-line stub into a full explanation of the text-tag mechanism itself.

Built these into `ChartGen_Tab_Guidance.pdf` using ReportLab, against a client-supplied style guide (NHSBN palette/typography, A4, cover + contents page, banded tables) — kept the palette as given despite ChartGen being an internal TBN tool, per user instruction. Used a two-pass build (throwaway pass to record real per-section page numbers via a zero-space `Flowable`, then a final pass with those numbers in the cover contents) so the contents page stays accurate regardless of how long each section's content runs.

User hosted the PDF on SharePoint; worked through several SharePoint URL formats (sharing-shortcut `:b:` links, `AllItems.aspx` folder views) before landing on the real direct file path, and confirmed the `#page=N` fragment works in their browser against that URL.

Updated `core/ui/common/guidance.py`: replaced all placeholder `bbc.co.uk` entries in `GUIDANCE_URLS` with the real SharePoint URL plus the correct page anchor per tab, and removed the stale `"details"`/`"config"` dict keys left over from an earlier session's tab removal (both confirmed with the user before applying). Sidebar intentionally left with no guidance link — no `"sidebar"` key exists in the mechanism, and the user chose not to add one.

By explicit user choice, the PDF and its build script were not saved into the project folder — they exist only on SharePoint and in this session's now-discarded sandbox.

---

## Session — Chart-type default-population fix + Running Order `placeholder` column removal

**Chart type default-population.** Implemented default-populating a blank `insert_chart` Running Order row's `chart_type_ref` with the first valid chart type for its resolved data shape (`chart_type_map.csv` order). First implementation was placed at Running Order generation time (`generate_from_template`) — wrong, since generation always precedes Fetch in the only possible workflow order, so `shape_type` is never known at that point; caught via live user testing. Corrected by moving the trigger to the end of Fetch: new `backfill_chart_types_after_fetch` (`import_flow.py`) calls shared logic in `generation.py` (`default_chart_type_ref_for_shape`, `backfill_default_chart_types`), invoked silently from `imports_tab.py`'s Fetch button handler. Only fills genuinely blank cells; never overwrites a set `chart_type_ref`. No user-facing message, by explicit request. Documented in Functional Spec §7.1.

**Running Order `placeholder` column — investigated and removed entirely.** Prompted by a question about whether the field was pointless. Traced its full lifecycle: captured at template-read time from the matched PowerPoint placeholder's name, but that placeholder object is deleted from the cleaned template the moment it's matched (Decision 13/§6.4) — so by the time any Running Order function runs, nothing in the live `.pptx` corresponds to the stored name. Confirmed via code trace across `assembly_engine.py`, `insert_picture.py`, and `insert_from_excel.py` that every content-insertion path works purely by EMU coordinate (`left_emu`/`top_emu`/`width_emu`/`height_emu`) and `slide_index` — never by placeholder-name lookup.

Its remaining uses were: (1) a UI caption and table column in `running_order_tab.py` (cosmetic/legibility only), (2) a per-row `ok_result` message in `insert_chart` naming the placeholder — traced further and confirmed this message is built and immediately discarded, since `batch_process.py`'s `run_batch` only ever surfaces a **per-unit** summary log, never the per-row `ctx.log` list, for any run mode including Run Selected against one unit — and (3) a dict key on `ctx.autotable_stats` inside `insert_chart`. (3) was flagged by the user as a genuine bug risk: placeholder names are only unique **per slide**, not across the whole Running Order, so two slides both containing a placeholder named e.g. "Chart 1" would silently overwrite each other's autotable stats once Autotables are built (currently inert, since nothing reads that dict yet).

Removed the column and every reference to it: `schema.py` (`COLUMNS`), `generation.py` (row templates, docstring), `xlsx_writer.py` (column-width map — read/write logic was already schema-driven), `row_ops.py` (stale comment), `assembly_engine.py` (`insert_chart`'s dead message and local variable; `empty_placeholder`'s equivalent, simplified to use `row_id`), `running_order_tab.py` (edit-dialog caption, overview table column). `xlsx_reader.py` required no change. `ctx.autotable_stats` re-keyed from placeholder name to `row_id` (Architecture Decision 11's existing row-identity convention).

Confirmed in passing that `PlaceholderInfo`/placeholder detection in `template_reader.py` is an unrelated, still-necessary concept (matching yellow boxes against real PowerPoint placeholders at template-read time) and was left untouched.

Docs updated: Architecture (Running Order column schema table — row removed), Functional Spec (§6.2, §6.3, §9.1, §9.2 — "named placeholder"/"references placeholders by name" language removed or reworded), Glossary (*Placeholder*, *Free-floating yellow box* — trailing "Running Order references it by name" clauses removed). No Feature List or Primer changes needed.

**Left open, by explicit user request:** the broader finding that the entire per-row `ctx.log` mechanism (every Running Order function's `ok_result`/`err_result` message) has no consumer anywhere in the UI. Not fixed this session — flagged in Next_Session.md for a future decision (give it a real consumer, or strip the dead message-building out of every function).

**Also this session:** Running Order overview table (`running_order_tab.py`) — `#`, `On`, `Slide` columns set to Streamlit's minimum named `column_config` width (`"small"`, 75px). Cosmetic only; not written up in the governed docs per explicit user instruction.


---

## Session — Yellow box detection rework, theme colour resolution, tolerance and Outputs tab fix

**Three-scenario yellow box resolution.** Replaced the requirement that a yellow box sit fully inside a placeholder with three outcomes: fully contained (matched to the placeholder, its position/size used), no overlap (free-floating — the box's own position/size used, named after its own PowerPoint shape name), partial overlap (ambiguous — left unclassified and unremoved, warned). Motivated by the discovery that PowerPoint placeholders can only be added via Slide Master/Layout, not drawn onto an existing slide, making the old rule unworkable for content added after a template's placeholders are fixed. Unrecognised yellow box content now warns (slide + text preview) rather than silently stripping; any template read with at least one warning gets a summary line prepended. Implemented in `template_reader.py`. Documented as Architecture Decision 13; Functional Spec §6.3/6.4, Feature List, and Glossary updated to match.

**Outputs tab batch-size slider crash.** `st.slider(min_value=1, max_value=min(50, max(remaining, 1)))` collapsed to `min_value == max_value == 1` whenever `remaining` was 0 or 1, which Streamlit rejects. Root cause traced: this had likely never been hit before because any template with a real chart URL trips the existing "unassigned chart type" setup check first, blocking the Outputs tab before the slider is reached — this test template had only picture/Excel content, so that guard never fired. Fixed in `outputs_tab.py` by showing a plain batch-size label instead of a slider whenever `remaining <= 1`; corrected a first-draft regression where the Reset queue button was accidentally only rendered in the slider branch.

**Theme-referenced fill colour detection (real bug, found via live testing).** User uploaded a real template (`Presentation_Example_2_Projects.pptx`) reporting yellow boxes not being detected. Investigation (reading shape XML directly) found most of the file's yellow boxes get their colour via PowerPoint's "Shape Styles" gallery — `<p:style><a:fillRef><a:schemeClr val="accent4"/></a:fillRef>` — storing no literal colour on the shape at all, only a theme pointer; confirmed `accent4` resolved to the exact colour (`#F2CB05`) the user reported as "not detected." `_get_shape_fill_rgb` rebuilt to resolve, in order: explicit literal fill, explicit theme-colour fill on the shape, and (new) the shape's style `fillRef` — each theme reference resolved through the slide's colour map (`clrMapOvr` override if present, else the slide master's `clrMap`) and the theme's `clrScheme`, walking the slide → layout → master → theme relationship chain via python-pptx (`shape.part.slide` → `.slide_layout` → `.slide_master` → `master.part.part_related_by(RELATIONSHIP_TYPE.THEME)`). Deliberately does not model `fillStyleLst` shade/gradient variants on non-idx-1 `fillRef`s — accepted simplification given yellow detection's already-tolerant HSV thresholds. Verified against the real file: all 5 previously-invisible chart boxes now detected and classified correctly. Documented as Architecture Decision 14.

**1mm containment tolerance.** Same test file surfaced a second issue once colour detection was fixed: a box whose edge was exactly 1 EMU outside its placeholder's (confirmed via coordinate inspection) — PowerPoint copy/paste rounding noise, not a real design gap — was being classified as "partial overlap" rather than "fully contained." Added a 36,000 EMU (1mm) tolerance to `_fully_contained` on each edge (`CONTAINMENT_TOLERANCE_EMU`). Verified: all 10 chart boxes across the file's paired-box slides now match correctly; only the two genuinely-empty (no text) yellow boxes on slide 12 still warn, correctly. Documented as part of Architecture Decision 14.

**Verification method.** All four fixes this session were tested by running the actual updated `template_reader.py` against the user's real uploaded `.pptx` in a sandboxed environment (not just code review) — theme colours, containment geometry, and warning output were all confirmed against real shape XML and real coordinates before being called fixed.

**Docs.** Functional Spec, Feature List, Architecture (Decisions 13 and 14), and Glossary updated in the static docs mirror. Not yet re-uploaded to Project Files as of this session's close.


## Session — Tweaks column and Base Chart statistics ownership reversal

Added a `tweaks` Running Order column and Charts sheet control, retyping every Base Chart function's `tweaks` parameter from an unused `list` default to a wired-through `string` (Architecture Decision 16).

User then questioned why Base Chart functions — whose job is producing a visual — were computing and returning statistics at all. Traced every consumer of the existing 4-tuple `render_chart` return (`base_summary_stats`/`layer_summary_stats`/`layer_units`) and found none of it was load-bearing: the Charts sheet preview already discarded `base_summary_stats`, and `AssemblyContext.summary_stats` was written once per chart in `assembly_engine.py` and never read back anywhere in the codebase. Also surfaced a genuine inconsistency: two different "Selected value" computation methods existed across NumericSeries chart functions of the same shape type, meaning the same unit/data could show a different Selected value purely depending on which chart type was picked.

Agreed direction: data shapes already passed to a chart are the source of truth for any statistics or unit lists needed; no intermediate transformation before use; the assembly engine's own copy of `population_layers` should be the source if that data is ever needed later (e.g. Autotables); Charts sheet stats/unit-list display should read directly from the data shapes with no transformation layer.

Implemented in full: all 20 Base Chart functions (four shape modules) now return `image_bytes` only; `_summary_stats_with_selection`/`_selected_layer_value` deleted from `base_charts/shared.py` (zero remaining callers); `registry.render_chart` simplified to a plain dispatch-and-return; `AssemblyContext.summary_stats` removed; `assembly_engine._render_chart_image` returns bytes only; `charts_tab.py`'s preview now calls `summary_stats_by_layer`/`units_by_layer` directly against `pop_layers` rather than via `render_chart`'s return value (Architecture Decision 17).

All six governed documents updated in the mirror to reflect both changes — Architecture (schema table, Decision 11, AssemblyContext diagram, Decision 15 trimmed, Decisions 16–17 added), Functional Spec (§9.3, §10.3, §10.5), Feature List (Charts sheet round-trip row, Autotables row), Glossary (AssemblyContext, CHART_SANDBOX_FIELDS, Autotable, Summary stats, Tweak entries). Primer and Docs Maintenance Guide unaffected. Re-upload to Claude Desktop Project Files confirmed pending at Close-down.


## Session — Base Charts Rewrite + Custom Charts Feature

Rewrote all 20 Base Chart functions as standalone artefacts: one file per `chart_type_ref` under `base_charts/{shape}/`, `shared.py` deleted, `report_context` dropped from every signature in favour of reading identity from the `"Selected"`-labelled `population_layers` entry — fixing a real inconsistency where `ranked_column`/`dot_strip` had previously used `report_context` while every other chart already used the population layer. Established the formal **chart_inputs** contract term (`population_layers, width, height, tweaks`).

Built the Custom Charts feature end to end: a user can download a self-contained bundle for any chart (contract + complete current code + live data), hand it to an AI, paste the result back in for static validation and live preview, and save it permanently into the workfile — indistinguishable from a built-in from that point on. New package `core/output_generation/execution/charts/custom_charts/` (`contract.py`, `gate.py`, `resolve.py`, `bundle.py`); storage mirrors the manifest/cache pattern (`WorkfileState.custom_chart_rows`/`.custom_chart_code`, `workfile_config/custom_charts/` in the `.cgw`); dropdowns merged at all three genuine listing sites (Charts sheet, Running Order dialog, Running Order xlsx), deliberately excluding `generation.py`'s auto-default-on-fetch.

Two real bugs surfaced through live user testing and were fixed: `bundle.py` extracted only the target function's source rather than its whole module, silently dropping every helper it depends on; `gate.py` rejected any file with more than one function at all, when every built-in legitimately carries several helpers alongside its one chart_inputs-signature entry point. Both fixed same session.

Agreed, but explicitly deferred: renaming `chart_type_ref` to `base_chart_name` everywhere, including the on-disk column — accepted as a breaking change requiring a file version bump, to be done as its own dedicated session.

Updated Functional Spec (new §10.0 Data Visualisation philosophy, new §10.9 Custom Charts, light edits to §9.1/9.3/10.1/10.3/§2) and Architecture (Section 4/5/6 updates, new Decision 18) in the mirror; both re-uploaded and confirmed current by the user. Feature List and Glossary not yet reviewed against these changes.


**Addendum — same session, Feature List and Glossary review:** Extended the documentation review beyond Functional Spec/Architecture to Feature List and Glossary, at the user's prompt. Found two genuine staleness bugs, not just missing new content: Feature List's `insert_chart` row and Glossary's `ReportContext` entry both still claimed charts receive `report_context`, which this session's Base Charts rewrite removed entirely. Both corrected — `insert_chart` now describes built-in-then-custom resolution and `population_layers`-based highlighting; `ReportContext` now states it's passed to text replacement only. Added a new Feature List row for Custom Charts and new Glossary entries for `chart_inputs`/`Custom Chart`. All four affected documents re-uploaded and confirmed current; Primer and Docs Maintenance Guide needed no changes.


---

## Session: Summary Stat Tags, Cut Resolution Consolidation, Charts Sheet Persistence

Built Summary Stat Tags end to end — a second table on the Text tab, short permanent base-36 tag ids each standing in for one summary-stats value from one chart's own independently-authored cut of its cached data (`hex_id`, a single population token, TimeSeries period/metric fields, a Reference id). New storage: `workfile_config/text_stats.csv`. Full authoring flow (define cut → tick statistics from a checklist → optional description → Add), live preview table (Data Source, Population, Statistic, Current value, Description columns), single-row delete, and an Excel download/upload round-trip (full-replace on upload).

Iterated the feature live against real testing feedback, finding and fixing several genuine bugs in the process:
- A `Region()`-style population token was being stored as its *resolved* value at creation time, freezing the tag to whatever peer group happened to be selected then — fixed by storing the token itself (re-resolved fresh against the current reporting unit on every use).
- An interim `layer_index` mechanism (letting a tag read one of several layers from a multi-token populations string) was introduced, then removed again once the populations control was restricted to a single token — a tag resolves to one value, so it only ever needs one population.
- The ticked-stats checklist and the Convert-to-Metrics period picker were both silently losing selections whenever they became momentarily unavailable (e.g. mid-way through switching to a different chart) — fixed by giving each field a persisted "record," reconciled against what was actually offered each render rather than filtered destructively.
- Fixing the above initially introduced a worse bug: the widget's live value was being overwritten on every single render, including the render where the user had just ticked something — since Streamlit commits a fresh interaction to session state before rerunning, this silently discarded every tick. Fixed to only rescue a widget's value when its options have genuinely changed shape since the last render.
- A `StreamlitAPIException` from writing to a widget's session-state key after that widget had already rendered in the same script pass — fixed with a pending-flag deferred-clear pattern.

Closed `update_text`'s one remaining documented gap: PowerPoint table cells are now covered, for both tag families (per-unit tags and Stat Tags), by extracting the paragraph-walk-and-collapse logic into a shared helper applied to both ordinary text frames and table cells alike.

Added Charts sheet sandbox-state persistence across Save/reopen (`settings["charts_sheet_state"]`), independent of the existing Running Order round-trip — the sandbox's current fields (bound row, cache file, chart type, populations, period range/metric-periods, tweaks, sizing, save-action/target) survive a Save and Open even if never explicitly committed to a Running Order row.

Consolidated a three-way code duplication: `insert_chart`, the Charts sheet, and Stat Tags each independently reimplemented the same "resolve a chart's own cut" pipeline (period trim, metric-periods conversion, population-table/target-rows/selected-ids resolution). Extracted into `core/shared/normalisation_containers/cut_resolution.py` (`prepare_chart_cut`). This forced two small module relocations to respect the one-way dependency rule: `parse_metric_periods_string`/`build_metric_periods_string` to `shared/infrastructure/period_ids.py`; `format_number`/`format_reference_value` to `shared/infrastructure/value_formatting.py`.

Made the workfile description field editable at any time (previously set only at New Workfile), and fixed chart dropdown ordering (Charts sheet, Stat Tags) to sort numerically by `chart_ref` rather than by cache filename (hex id) or plain string comparison.

Some UI density and heading polish on the Imports, Populations, and Text tabs, matching the Outputs tab's existing compact style.

All six governed documents reviewed; Feature List, Functional Spec, Architecture, and Glossary updated (Architecture Decisions 19–22). Primer and Docs Maintenance Guide needed no changes.


## Session — Output Tables

Built Output Tables end to end: a full second content-construction pathway alongside Charts, mirroring its architecture throughout. Grid model (own spreadsheet-shaped storage, corner-cell id, column-width/row-height percentages), an Output Tables tab (one shared "Select Table" box driving both Edit Grid and a Preview sandbox), ten built-in Base Tables (`plain_grid`, `table_ledger`, `table_zebra`, `table_editorial`, `table_terminal`, `table_cardtile`, `table_pill`, `table_freeform`, `table_brutalist`, `table_softui`), Custom Tables (download/paste-back/validate/preview/save, mirroring Custom Charts), `insert_table` as the new Running Order function, and a `[Table:name,Rows:X,Columns:Y]` yellow-box grammar for template-driven creation. `table_cardtile` was iterated twice live. Chart-component cells (`{n}`) were deliberately parked, not built.

Found and fixed two real cross-cutting bugs during testing: a table/chart sizing conversion that clamped rendered resolution to a fixed 7.5in reference, causing genuine image quality loss on any row exceeding it (affects the chart rendering path too, not just tables); and a Streamlit widget-mount timing issue in the new Preview sandbox where a Sizing box showed a stale value on first entry into Preview mode despite the underlying value being correct throughout. Also fixed two Streamlit crashes (`StreamlitAPIException` from writing to an already-instantiated widget's session-state key; `StreamlitDuplicateElementId` from two tabs sharing an unkeyed button, since Streamlit runs every tab's code every rerun regardless of visibility).

Investigated a PDF-export image-pixellation complaint thoroughly: tried raising rendering DPI (300→450, no visible change), forcing `autoCompressPictures="0"`, and swapping `ExportAsFixedFormat` for `Presentation.SaveAs(...,32)` — a genuine improvement, but not a full fix. Reviewed and ruled out LibreOffice (different rendering engine, fidelity risk to the template), third-party PDF printer drivers (confirmed via their own documentation that printing structurally cannot carry hyperlink data), Adobe Acrobat PDFMaker automation (Adobe's own SDK guidance restricts automated/server use without a separate licence), and slide-image export + reassembly (loses selectable text and requires reconstructing hyperlinks by hand). Accepted as a known PowerPoint-inherent limitation for now — see Architecture Decision 26.

Added a new shared helper, `core/shared/infrastructure/id_generation.py`, refactoring Stat Tags' own id issuance onto it alongside Output Tables' `table_id`. Added a new Architecture principle, "Validate only where designed" (Structural Design Principles), prompted directly by the sizing-clamp bug.

All four applicable governed documents updated (Feature List, Functional Spec, Architecture, Glossary); Primer and Docs Maintenance Guide needed no changes.
