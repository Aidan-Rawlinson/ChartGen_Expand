<!-- Purpose: Significant decisions and the reasoning behind them. Kept separate so rationale does not get buried in the Progression_Log. -->

## Session: Installer, update mechanism, and versioning

- Install location: %LOCALAPPDATA%, no admin rights required. Chosen given this is a purely local, internal tool and no admin access was assumed for this phase.
- Two independent version identifiers adopted: software id (this build) and file version id (a .cgw's internal structure), rather than one shared version number. An incompatible file version id is a hard refuse at Open, with no migration attempted for now - expanding compatibility later is an explicit non-goal for this phase.
- The local side of the Check for Update comparison uses the existing software_id from version_compatibility.csv, not PE metadata of a local executable, since ChartGen itself runs from Python source rather than a compiled binary. Only the SharePoint-side release copy is a real Windows executable, so PE metadata reading applies only to that side.
- Version comparison is normalised (parsed into numeric tuples, padded with zeros) rather than exact string matching, so short forms like "0.0.1" correctly match the four-part "0.0.1.0" that Windows PE metadata always produces.
- Check for Update is a manual sidebar button only, gated to no-workfile-open, not automatic and not a background poll. Chosen for simplicity given updates are expected to be rare, and to keep failure handling simple (no silent background-check failure states to design for).
- OneDrive-for-Business path resolution is dynamic, via the OneDriveCommercial environment variable with a folder-scan fallback, never stored and never asked of the user. Chosen over authenticated direct SharePoint URL access (Graph API / MSAL), which would need an Azure AD app registration and token handling for no real benefit over the simpler filesystem-path approach already used elsewhere in the codebase for workfiles.
- The update flow copies the installer to a temp folder, launches it via subprocess, then hard-exits ChartGen's own process (os._exit), since a running process can lock its own files on Windows and a normal Streamlit shutdown isn't designed to be triggered from within a callback.
- AppId in the Inno Setup script is fixed forever, never to be changed across releases - this is what makes re-running the installer register as an upgrade rather than a fresh install.
- __pycache__ and .pyc files are explicitly excluded from the installer's file list - stale bytecode, not source, regenerated on first run.
- The version-control behaviour (file version compatibility) was documented in Functional Spec only, not split with Architecture, per explicit user instruction to pick a single home rather than spread the same fact across two documents.
- CHARTGEN_VERSION (a separate hardcoded constant in workfile_file.py) was consolidated into version_compatibility.csv's software_id, removing a second, redundant source of truth for the same concept.


## Session: Expansion planning and Step 1 — the manifest table

- Architecture Decision 9 (application location) deleted entirely rather than rewritten: the installer exists but code still sits on C: under developer control — the decision no longer added value and the situation is nuanced.
- Seven-step expansion plan lives in Current_State.md, not a new file: it is rewritten each session anyway, and the Session Start protocol only reads the four named dynamic_docs files.
- One .cgw will no longer map to one project/year — that was proof-of-concept simplicity. A workfile must reach the same project across multiple years, and other projects. Same project_id + different year = a different project.
- Credentials move from upfront login to just-in-time collection. Fail-soft chosen over chasing: if a fetch lacks credentials, it fails with a clear message telling the user to enter them, rather than interrupting with a credential prompt.
- Manifest consolidation: the chart URL table and the cache manifest were one column apart in scope (shape_type), so they were merged into a single data_cache/manifest.csv rather than kept as two synchronised stores. CSV chosen over JSON per the Architecture's existing flat-table rule; located in data_cache/ because the table is the index to the cache it sits beside.
- hex_id (5-digit hex, never reused, including deleted rows) is the storage identity; chart_ref (Chart_0001) is display-only and renumbers freely. Deliberate paranoia split so deletion/renumbering can never corrupt data identity.
- Deleted manifest rows are marked, not removed: hex_id stays reserved, cached data kept. Excel reimport deletes by omission; template re-upload containing a deleted URL resurrects the row under its original identity (a yellow box is a clear statement the chart is wanted).
- Running Order generation stays at template-processing time even though data is no longer fetched then (option (a)): rows get cache_file={hex_id}.json immediately, chart-type dropdowns constrain only after first fetch.
- The chart URL table is read-only in the UI; editing is via the Excel round-trip only. An in-table editor was built and then removed at the user's request after live testing — one editing route, consistent with how users actually work.
- The manifest Excel export excludes chart_ref (renumbered on import, exporting it invites conflicts) and carries hex_id as the round-trip identity; 300 blank formatted rows appended for user input.
- File version 0.0.2 bumped immediately with the structure change rather than accumulated to the Tidy step; no migration from 0.0.1, per the established hard-refuse model.


## Session: Multi-project population tables, chart-population resolution, and New Workfile streamlining

- **"soft_parents" over "parent."** Relationship columns between population tables are named `soft_parents`, never `parent`/`parents` anywhere in code — "parent" implies strict one-per-row cardinality, which these relationships don't have (one-to-many, many-to-many, and multiple-independent-links all occur). The rationale lives in code comments, not in a user-facing explanation — the naming is for Claude/future maintainers, not the end user.
- **soft_parents recorded on the child side only.** No reverse reference on the parent-side table; resolving "what links to this row" is a reverse lookup across other tables, not a stored field.
- **Every population table carries identical headers.** Only the count of `Name()` peer-group columns is allowed to vary between tables. Fields specific to one table's source (e.g. `submission_service_count`, `nhs_code`, `project_id`) were deliberately dropped rather than carried as asymmetric columns.
- **Master table = position 0 in `table_order`, full stop.** No separate "is master" flag exists or should exist; reordering a table to the top position is what makes it master.
- **Relationship resolution is one hop only, by design.** Deliberately not walked recursively; revisit only once a genuine multi-level chain is a real, non-hypothetical need.
- **Population-table creation is fully automatic, with no user-facing trigger.** Triggered inside the toolkit fetch, per chart, on first encounter of a new project/year. Superseded an earlier plan for a manual "Add Project" feature.
- **`acquisition` must never depend on `workfile.setup`.** This is why population-table building logic (`add_project_tables`, `build_organisations_table`, `build_submissions_table`) moved out of `workfile.setup.new_workfile` into `acquisition.toolkit_nhs.population_tables` — the automatic trigger requires `fetch.py` to call it directly.
- **Workfile creation and population-table creation are permanently divorced processes.** `create_new_workfile` must never gain knowledge of projects, years, or population tables, even for convenience.
- **Workfile-level settings hold no project identity.** No year, project_id, or project_name at the `settings.csv` level — none of them are workfile-level facts once a workfile can span multiple projects. Each population table names its own project/year in its table name; each fetched chart carries its own via its URL.
- **The workfile description field is for the person, not the system.** Free text, shown in the app header, plays no role in file naming, table resolution, or any other logic.
- **Native OS Save dialogs replace the app's own folder-picker-plus-name-box UI**, for both New Workfile and Save As — including relying on the OS dialog's own overwrite confirmation rather than building a duplicate app-level step.
- **No Base Chart renders a title** — applies uniformly to both the Charts tab preview and generated report output, since both share the same rendering pipeline.
- **The Docs Maintenance Guide no longer has a "Refactoring Issues" document or concept.** This phase is new functionality, not a refactor; deferred/known gaps are recorded as Notes on the relevant Feature List row instead. The Guide now governs five documents.


## Session — Second Toolkit (Indicators) and Credentials Relocation

- Login gate removed entirely; credentials validated on demand from a single box in the Config tab, not required to launch or use most of the app.
- One shared credential set/token authorises both the NHS and Indicators APIs — confirmed via source VBA. No per-database credential boxes.
- Save attribution (`last_saved_by`) is blank, not OS-username-defaulted, when no credentials have been validated this session.
- TimeSeries data shape's period axis lives once on the shape (shared across every Metric-Series in it), not per metric — a data shape represents one dataset.
- API-supplied period stats (`dateAverages`/`dateMedians`/`calculatedNationalAverages`) are dropped entirely for TimeSeries; stats are always recomputed locally per period, matching every other shape's convention. `calculatedNationalAverages` specifically is never adopted at all.
- Indicators toolkit's own period ordering (`availableDates`) is trusted as-is, not re-sorted — mirroring the source VBA rather than attempting to "fix" it.
- Organisation ids are assumed to match between the NHS and Indicators APIs, for now — an assumption to revisit if it proves wrong, not a verified fact.
- `submissions_timeseries_{project_id}` population table merges on every fetch (not build-once) and carries `Region()`, sourced from `nhs_organisations` at merge time, keeping the identical-headers convention across every population table.
- `GetVisibleDates`'s hardcoded project `42` (a VBA quirk) is not replicated — the actual parsed `project_id` is used.
- The VBA's `GetInfo`/tiers endpoint is deliberately not implemented — its only extracted value is unused elsewhere in the source.
- Chart rendering for TimeSeries is explicitly out of scope this session — data acquisition only; the Base Chart module is next session's work.
- Fetch progress across both toolkits reports as one continuous total, not two separate phases — corrected on request.


## Session — TimeSeries charting, Primer maturity statement

- **Primer maturity-statement anchor.** Rather than rewriting the Primer's tone throughout, agreed a single anchor sentence at the top of Section 1 stating ChartGen is under active development by a single developer and pointing to the Feature List as the built-vs-planned authority. Confident design-intent language elsewhere in the Primer is left as-is — it describes what the system is built to do, which is true regardless of how much has landed; the anchor just frames it correctly for a reader encountering the Primer in isolation.
- **TimeSeries Base Charts read shape data directly rather than reusing the NumericSeries-shaped helpers in `shared.py`.** Those helpers (`_get_selected_unit`, `_resolve_unit_colours`, `_selected_layer_value`) assume one scalar value per unit. A TimeSeries value is a vector indexed by period, so the new charts read `metric.units[...].values`/`period_stats` directly instead — the same reason NumericCompositional/CategoricalCompositional charts don't use those helpers either. No changes made to `shared.py`'s existing helpers.
- **`full_lines_linechart`'s background lines use alpha, not a flat light colour.** Confirmed via a quick design-literature check that the standard "spaghetti plot" technique specifically relies on transparency, so overlapping density in the population is visible, not just a flatly de-emphasised set of lines.
- **Legend entries use a proxy-artist pattern (empty `ax.plot([], [])`) rather than labelling every unit's line.** Needed because a population layer can legitimately hold more than one unit (the documented one-to-many `Selected` case, or a multi-unit peer group) — labelling per-unit would duplicate legend entries.
- **Organisation-identity mismatch between the NHS and Indicators toolkits is now being treated as a likely real problem, not just a documented assumption to revisit.** User's explicit instruction: any lookup-table fix must be applied at the earliest point in the pipeline — before the `soft_parents` link between a submission and an organisation is formed — not as a patch on top of the existing link. Full scoping deferred to a future session by user request.
- **Installer release status is no longer an active tracked item.** User explicitly asked not to be prompted about it while the project remains solo/early-stage; dropped from Next_Session/Current_State open questions accordingly.


---

## Session — Charts Sheet / Running Order Two-Way Sync

- **Charts sheet owns the sync entirely; Running Order stays passive.** The Charts sheet reads a Running Order row and writes back on explicit Save; the Running Order tab/store never pushes to, or flags anything for, the Charts sheet.
- **Round-trip fields live in one maintained list (`CHART_SANDBOX_FIELDS`), not hardcoded per call site.** Chosen specifically so future chart-viz-related Running Order fields (e.g. Tweaks, when built) ride the same sync mechanism without reworking it — the field list is expected to grow over time.
- **Free-play (loading a dataset with no bound row) keeps full save-back capability** (Overwrite/Insert above/Insert below + target-row control), not just a read-only preview — the two entry modes are disconnected only at the load end, not the save end.
- **Major, shape-specific analytical fields (e.g. a future TimeSeries period-cut) get their own named, shape-gated Running Order column — never folded into Tweaks.** A tweak is a minor, rendering-only adjustment; a field that changes which chart types are even valid for the data is an analytical choice, structurally the same category as `chart_type_ref` itself.
- **Rows referenced by `row_id`, not list position or a descriptive label.** `row_id` survives an Overwrite; an Insert renumbers it, so sandbox state referencing a specific row is cleared after every save rather than trying to track a moving position.
- **Sizing unit is percent of the page's shorter dimension, not raw EMU, and this applies universally** — both entry paths, always, not just as a free-play convenience. Real template page size (captured once at template processing) always wins over the manual/standard-size dropdown once known.
- **Screen zoom is a separate, purely cosmetic control** — never stored, never affects the real (percent/EMU) size fields. Placed in its own last-in-rail expander rather than beside the fields that do save, once the rail was reorganised around "what saves vs what doesn't."
- **Dropdown "no selection" sentinels are plain strings, not Python `None`.** `None` pre-set into `session_state` before a Streamlit widget's own creation collides with Streamlit's internal "no selection" placeholder handling, overriding a custom `format_func`. Applies to all three of the Charts sheet's row/dataset dropdowns.
- **Front-end density/layout tuning done with native Streamlit only (no custom CSS) for this session**, per explicit instruction — `label_visibility="collapsed"`, `st.expander` default states, `st.columns` ratios, icon-only buttons. A true square/fixed-pixel button remains a known native limitation, left unresolved by choice.


---

## Decision — Organisation identity mapping: live per-project lookup, not a static CSV

**Context.** The Indicators (ics) and NHS toolkits' organisation id spaces were confirmed not to match. A static CSV extract of the mapping was built first as a stopgap, then a live source of the same mapping was discovered on the same project-submissions endpoint already being called for visible dates.

**Decision.** Retired the static CSV approach entirely. The live per-project `userOrganisations` data (from `/projects/{id}/submissions`) is now the sole source of the ics-organisation-id → nhs-unit-id mapping, and of real submission names. No fallback to a static file.

**Rationale.** The live data requires no manual upkeep, can't go stale, and was already being fetched for an unrelated purpose (visible dates) — using it costs nothing extra. A static CSV would have needed periodic manual refreshes against a data source expected to be superseded within about a year; retiring it removes that maintenance burden entirely rather than just deferring it.

**Decision.** When a submission's organisation resolves to an nhs unit id not yet present in `nhs_organisations`, enrich it via `toolkit_nhs.api_client.get_organisations`, queried against the current calendar year — confirmed with the user as the correct stand-in, since Indicators data has no year concept of its own (periods only).

**Decision.** An organisation_id with no live mapping entry does not get any invented fallback — no soft_parents link, Region() left blank, and the fetch surfaces exactly one aggregated warning per run (not per submission). Explicitly the user's instruction: "nothing is the best solution providing it is obvious... otherwise the bare minimum we can get away with." Resolving the underlying data gap is treated as the user's job (fix the source data), not something the code should paper over.

---

## Session — TimeSeries period handling + population-table Excel round-trip

- **Population table Excel round-trip lives in `shared/infrastructure/`**, not alongside the manifest table's own xlsx pair in `acquisition/manifest_table/` — it's generic across any population table and NHS/Indicators-agnostic, the same reasoning as `cache_writer.py`'s earlier move (Architecture Decision 10).
- **Population-table Excel edits get no validation for now.** User: "the table by its nature has to be incomplete at times, and possibly even wrong at times" — a partial validation pass now would be the wrong shape of fix. Proper table-wide validation deferred as a distinct future piece of work, not bundled into this session's round-trip.
- **Period Range and Convert Periods to Metrics have deliberately different error behaviour** for an unresolvable period_id: Period Range → silent empty range (consistent with the existing "unresolvable population token" convention); Convert Periods to Metrics → hard error, row halts. Both confirmed explicitly by the user, not inferred.
- **Convert Periods to Metrics handles multiple source Metric-Series**, not just the first (unlike existing TimeSeries chart rendering, which only renders the first). Output ordering is metric-major (all periods for metric 1, then metric 2, etc.), not period-major. Naming format is `"MetricName (PeriodLabel)"`.
- **`shape_transforms.py` is a new top-level module** under `shared/normalisation_containers/`, not inside `shapes/` — converting between two shapes needs to know about both without either shape module depending on the other, the same reasoning as `url_triage.py` sitting outside both toolkit packages (Architecture Decision 10).
- **Excel period dropdowns use a hidden list sheet**, not inline list formulas — inline lists are capped at 255 characters by Excel itself, too short for a chart's full period history. One column per distinct cache_file, shared by all three period columns and all rows referencing that cache_file.
- **`metric_periods`'s Excel dropdown is single-value, same hidden-sheet mechanism as `start_period`/`end_period`**, even though the field itself can hold several `^`-delimited ids — Excel has no multi-select list validation, so the dropdown is a convenience for adding one value, not a hard constraint on the cell's final content. User's explicit steer after initially building it as unvalidated free text.
- **Built a chart-type reconciliation check on Excel upload, then removed it whole** at the user's request, rather than leaving it in unused. No dead code retained for "maybe later" — the eventual table-wide validation will be scoped fresh when it's actually tackled.


## Session — Quick wins, login rebuild, tab consolidation, sidebar polish

- **Number formatting is `format_modifier`-driven, applied uniformly across every base chart.** No modifier → `#,###`; `"P"` → `#,##0%`; `"C"` → `£#,##0`. Applies to axis ticks and inline value labels alike. `CategoricalCompositional` is the one deliberate exception — its values are always proportion-of-whole percentages by chart design, independent of `format_modifier`.
- **Native Text placeholders are permanently excluded from yellow-box matching.** Confirmed as a bug fix, not a scope change under discussion — a Text placeholder should only ever receive `update_text` tag replacement, never chart/picture/excel content via a yellow box. `PP_PLACEHOLDER.BODY` removed from `_is_chart_placeholder`'s eligible set for good.
- **A matched placeholder is now removed from the cleaned template alongside its yellow box.** Its position/size is already captured in the Running Order; content is inserted by coordinate at generation time, not via the placeholder object. Unmatched placeholders are left in place.
- **Sign-in is now a mandatory, page-level gate — not on-demand from a Config tab.** Decided because only one credential set is needed for the foreseeable future (a second database is months away) and a user-facing tool was needed within days, making the earlier "maybe we'll need two logins" caution moot. This is a permanent architectural change, not a temporary workaround.
- **Details tab and Config tab both removed from the tab bar permanently.** Details' content relocated to a sidebar expander; Config's reference-CSV placeholder scope dropped outright — the ics lookup-CSV use case it was reserved for was superseded by an API endpoint, so there's no foreseeable purpose for it. Explicitly revivable later "if we find a clear purpose," per the user, but not kept as a placeholder tab in the meantime.
- **Per-tab guidance links live inline next to each tab's own title, not as a sidebar button.** Chosen because `st.tabs()` cannot report which tab is active into `session_state`, ruling out a single adaptive sidebar button. Each tab's own render function carries its own link instead, which needs no active-tab detection at all.
- **Sidebar divider line between button groups: attempted extensively, then explicitly dropped by the user.** Plain spacer divs (no line) are the accepted final state. Not to be revisited via the same techniques (margin/padding/fixed-height flex box/absolute positioning) without understanding the root cause first, per the user's own call to stop spending time on it.
