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

## Session — Prototype-sharing prep

- **No functionality changes during prototype-sharing prep**, guidance links/content excepted. Explicit user call at the start of this work.
- **No known-issues briefing for the colleague.** User ruled this out — it's a look/feel/usability prototype, not an alpha or beta, so untested-detail caveats aren't being surfaced.
- **No pre-built sample workfile for the colleague.** New Workfile flow is smooth enough on its own; user is instead building sample PowerPoint templates (two or three, varying complexity) for the colleague to run through the system themselves.
- **Guidance content structure: one PDF, one page per tab, linked via `#page=N` anchors** — chosen over separate hosted pages per tab, to keep `GUIDANCE_URLS` pointing at a single hosted file.
- **Keep the client-supplied style guide's NHSBN colour palette/branding as given**, despite ChartGen being an internal TBN tool rather than NHSBN member-facing — explicit user call.
- **Full cover + contents page** in the guidance PDF, rather than a lean reference doc — explicit user call.
- **Removed stale `"details"`/`"config"` keys from `GUIDANCE_URLS`** (dead code from an earlier session's tab removal) — confirmed with the user before applying.
- **Sidebar has a guidance PDF page but no in-app guidance link** — no `"sidebar"` key added to `GUIDANCE_URLS`; user chose to leave it unlinked rather than add a new UI element for it.
- **The guidance PDF's build script and output were not saved into the project folder** — user explicitly declined persistence; regenerating or updating the guide later will mean rebuilding it from scratch.

---

## Session — Chart-type default-population + Running Order `placeholder` column removal

- **Chart-type backfill trigger point: end of Fetch, not Running Order generation.** Running Order generation always precedes Fetch (no code path exists where it doesn't), so `shape_type` can never be known at generation time. The default-population logic lives in `generation.py` but is invoked from a new `import_flow.backfill_chart_types_after_fetch`, called once at the end of the Fetch action. Silent — no user-facing message, even summarising how many rows were backfilled.
- **Backfill never overwrites a set `chart_type_ref`.** Only genuinely blank cells are filled, whether the existing value came from a manual edit or a prior backfill. Idempotent on repeat fetches by construction.
- **Running Order `placeholder` column removed entirely — not deprecated, not left blank, deleted from the schema and every reader/writer.** Decided after tracing that it was never a live reference at runtime (the named PowerPoint object is deleted from the cleaned template once matched) and after finding it carried a real collision risk as a dict key (`ctx.autotable_stats`), since placeholder names are only unique per slide. `ctx.autotable_stats` now keys on `row_id` instead — the Running Order's own real row identity (Architecture Decision 11), not a template-derived label.
- **The per-row `ctx.log` mechanism (dead — no consumer anywhere in the UI) is deliberately left alone for now**, at the user's explicit request. This is a known, documented gap (see Current_State.md / Next_Session.md), not an oversight — revisit only when explicitly raised again.
- **Column-width and other pure-formatting decisions in the Streamlit UI are out of scope for the five governed documents.** Confirmed explicitly by the user this session: the governed docs describe behaviour, structure, and readiness — not minor display/formatting choices. Applies going forward, not just to this session's column-width change.


---

## Session — Yellow box detection rework, theme colour resolution, tolerance and Outputs tab fix

**Decision: replace "yellow box must be fully inside a placeholder" with a three-outcome resolution model.** Placeholders can only be added via PowerPoint's Slide Master/Layout system, not drawn onto an existing slide — making the old rule unusable for ad hoc content added after a template's placeholders are fixed, which is the expected common case, not an edge case. Chosen resolution, checked in order: fully contained → matched to placeholder (as before); no overlap → free-floating, box's own position/size used; partial overlap → ambiguous, left alone entirely (not classified, not removed, not added to the Running Order), warned. Partial overlap is deliberately rejected rather than guessed at — there's no reliable signal for which bounds (box's or placeholder's) were intended, so the designer is asked to resolve it themselves (move fully in or fully out).

**Decision: unrecognised yellow box content is now warned, not silently stripped.** Previously matched no category → stripped from the cleaned template with no signal at all. Now raises a warning naming the slide and a text preview. Any template read producing at least one warning (of any kind — unrecognised content, ambiguous overlap, multiple boxes matched to one placeholder) gets a single summary line prepended, so a partial failure is visible without reading the full detail list.

**Decision: resolve theme-referenced ("Shape Styles") fill colours, not just literal fills.** A yellow box styled via PowerPoint's Shape Styles gallery stores no colour on the shape itself, only a `<p:style><a:fillRef><a:schemeClr>` pointer into the theme. Chosen to resolve this properly rather than requiring users to always use literal/explicit fills: walks the full slide → layout → master → theme chain, resolving the colour map (respecting a slide-level override) before the theme's colour scheme, rather than a shortcut direct name lookup — the more thorough option was chosen deliberately given the cost difference was small (~20-30 extra lines) relative to the risk of a silent, hard-to-diagnose detection gap for any template using a non-default colour map.

**Decision: don't model shaded/gradient `fillStyleLst` variants on non-flat `fillRef`s.** The theme's format scheme can technically define a `fillRef` idx as a shaded or gradient variant of the base scheme colour, not a flat solid. Chosen not to model this — the base scheme colour is used unmodified. Accepted given yellow detection's HSV thresholds already tolerate meaningful colour drift; revisit only if a real template surfaces a visible mismatch.

**Decision: add a 1mm (36,000 EMU) tolerance to the "fully contained" check.** A copy/pasted shape in a real template showed a 1 EMU discrepancy against its placeholder — sub-visible rounding noise, not a real design gap — which the previous exact-integer check misclassified as a partial overlap. 1mm chosen as comfortably larger than any realistic rounding artefact while still far smaller than anything a person could perceive or intend as a genuine partial overlap.

**Decision: fix the Outputs tab batch-size slider by removing the slider, not by clamping its range.** When `remaining <= 1` there's no genuine range to choose a batch size over, so rather than forcing `min_value`/`max_value` apart artificially, the slider is replaced with a plain "Batch size: N" label in that case. Reset queue remains visible in both branches (a first-draft version accidentally scoped it to the slider-only branch — corrected before finalising).


## Session — Tweaks column and Base Chart statistics ownership reversal

- **`tweaks` is a string, not a list.** Every Base Chart function's `tweaks` parameter was typed `list` but never read; retyped to `tweaks=""` across all 20 functions plus `registry.render_chart`, matched by a new Running Order `tweaks` column. See Architecture Decision 16.
- **Base Chart functions return `image_bytes` only — no statistics, no unit lists.** A chart-rendering function's job is producing a visual; statistics and unit lists are a property of the data shape, read on demand by whichever consumer needs them, not computed or relayed by the charting layer. This reverses the 4-tuple `render_chart` return and the `AssemblyContext.summary_stats` storage introduced in an earlier session (documented in the prior account of Architecture Decision 15) — that mechanism had no real consumer and had produced a genuine inconsistency (two different "Selected value" computation methods across chart functions of the same shape type). See Architecture Decision 17.
- **Any future Autotables implementation reads directly from `data_shape`/`population_layers` already in scope inside `assembly_engine.insert_chart`** — no dedicated collection/storage mechanism is to be (re-)built ahead of that feature actually existing.


## Session — Base Charts Rewrite + Custom Charts Feature

- **Every Base Chart, built-in or custom, must be a fully standalone function with no imports from ChartGen's own code** — required, not just preferred, once it became clear a custom chart's download bundle would need to hand over `shared.py`'s contents as inline text anyway to make the bundle self-explanatory. Treated the same way an Excel `.crtx` chart-type template is treated: a rendering artefact, not application logic.
- **`report_context` dropped from every Base Chart's signature.** Everything it supplied (`unit_code`, `unit_id` for matching) was already duplicated in the `"Selected"`-labelled `population_layers` entry; keeping it around was pure redundancy and the source of a real inconsistency between chart functions.
- **The 20 built-ins moved from 4 shape-grouped files to one file per `chart_type_ref`**, so a built-in and a user's custom chart are structurally identical — no special case for "ours vs. theirs."
- **Custom Charts: static validation only ("AST gate"), no runtime sandboxing.** Explicitly chosen over sandboxed execution — internal, SharePoint-shared, colleague-to-colleague trust model, same level of trust already extended by sharing `.cgw` files at all.
- **The gate counts functions by chart_inputs-signature match, not by raw function count.** Any number of helper functions are allowed alongside the one entry point — matches how every built-in already works, corrected after an initial (wrong) "exactly one function total" rule was caught before it caused user-facing friction.
- **The in-progress ("temp") custom chart is never written into `WorkfileState`.** It lives only in ordinary Charts-sheet sandbox state, so it structurally cannot appear in any chart-type dropdown — not filtered out after the fact, never a candidate in the first place. `"temp"` and any built-in/existing-custom name are reserved and rejected as save targets.
- **Custom Chart storage mirrors the manifest/cache pattern exactly** — an index file (`custom_charts.csv`) plus one `.py` per entry, under a folder-per-shape layout matching the built-ins' own structure.
- **`chart_type_ref` → `base_chart_name` rename agreed, explicitly deferred** — accepted as a breaking change (file version bump, existing workfiles won't open), reserved for its own dedicated session rather than folded into this one.
- **Existing Functional Spec section numbers (9.1–10.8) left untouched** when adding new charting content, to avoid a renumbering cascade into Architecture/Feature List/Glossary's cross-references — new content added as 10.0 and 10.9 instead.


---

## Session: Summary Stat Tags, Cut Resolution Consolidation, Charts Sheet Persistence

- **Stat Tag anchor is `hex_id`, not `chart_ref`.** `chart_ref` renumbers whenever the manifest table changes; a tag anchored on it would silently start pointing at the wrong chart's data. See Architecture Decision 19.
- **A Stat Tag's populations field is a single token, not a populations string.** A tag resolves to one value, so it only ever needs one population, unlike a chart's own populations string (an ordered set of layers). An interim `layer_index` design (tracking which of several layers a tag read from) was built, then deliberately removed once this restriction was agreed — not left as unused scaffolding.
- **A `Region()`-style (empty-bracket) population token is re-resolved fresh every time, against whoever is currently selected — never stored as its resolved value.** This was the key correctness fix of the session: storing the resolved value (e.g. "South East") would freeze a tag to that value, breaking the moment a different organisation (in a different region) was selected. Confirmed as a "must not guess or fuzzy-match" requirement — either a recorded value is an exact match for the current context or it isn't; no approximation.
- **Tag ids are a persisted, monotonically increasing base-36 counter, never recomputed from surviving rows.** Recomputing after a delete would let a freshly-issued tag reuse an id some other, still-untouched piece of template text already points at.
- **Stat Tags storage is a flat table (`text_stats.csv`), one row per tag, no relational structure** — mirrors the Running Order's own convention rather than introducing a new pattern. Confirmed acceptable that several tags sharing the same underlying "cut" repeat those fields independently, since the authoring form (not storage) is what absorbs the repetition.
- **Stat Tags Excel round-trip is full-replace on upload, not identity-merge.** Confirmed explicitly acceptable for a row to simply be deleted if absent from the uploaded file — no cached data of its own needs preserving behind a soft-delete flag, unlike the manifest table.
- **The "keep only what's currently valid" pattern used elsewhere (e.g. the Charts sheet's own populations/metric-periods clamps) is not always correct** — it destroys a value that's only *momentarily* invalid mid-reconfiguration (e.g. switching chart before a new period is picked). Fixed for Stat Tags' own Convert-to-Metrics picker and ticked-stats checklist via a persisted "record," separate from the widget's own displayed value, reconciled only against what was actually offered on a given render. Worth applying this same pattern if the same symptom (a selection disappearing when its options briefly change) shows up elsewhere.
- **`update_text` table-cell support required no table-specific logic** — a PowerPoint table cell's `.text_frame` exposes the same interface as any other shape's, so the existing paragraph-walk logic was simply extracted into a shared helper and applied to both.
- **Charts sheet sandbox state is now persisted independently of the Running Order round-trip** — capturing whatever's currently in the sandbox, not just what's been explicitly saved to a Running Order row, on every Save/Save As/Save and Close, restored once per Open. Zoom and an in-progress Custom Charts paste-back are deliberately excluded.
- **The "resolve a chart's cut" pipeline (period trim, metric-periods conversion, population-table/target-rows/selected-ids resolution) is now a single shared function** (`cut_resolution.prepare_chart_cut`), used by `insert_chart`, the Charts sheet, and Stat Tags alike, after being found independently duplicated in all three. The final `build_population_layers` call is deliberately left to each caller, since the Charts sheet needs `target_rows` before it knows its own populations string.
- **Chart dropdowns (Charts sheet, Stat Tags) sort by `chart_ref`'s trailing number, numerically — not by cache filename (hex id) and not by plain string comparison** (which only gives correct order while every ref shares the same digit-width).
- **Formatting/UI-density decisions from this session (tab spacing, column widths, heading renames) are intentionally not recorded here** — the user asked that this record cover functionality only.


## Session — Output Tables

- **Tables render as images, the same way charts do — no native PowerPoint table population.** A table is a grid composited by a Base Table function into a single image, inserted like any picture. This is why Autotables (auto-populating a native PowerPoint table from chart statistics) is now superseded rather than pursued — the same rendering process covers the need.
- **Output Tables get their own tab and their own storage, not an extension of the Charts sheet.** An Output Table's grid/content model doesn't fit `CHART_SANDBOX_FIELDS`, and the user was explicit that tables needed a genuinely new authoring surface, not fields bolted onto Charts.
- **Base Tables and Custom Tables mirror Base Charts and Custom Charts structurally, but are kept as independent copies, not shared code.** `custom_tables/contract.py` duplicates (rather than imports) the chart domain's allowed-imports/banned-names lists, so the two rendering domains can diverge safely in future without cross-risk.
- **Chart-component cells (`{n}`, a saved chart embedded in a table cell) are explicitly out of scope for this pass.** Recognised by the grid's grammar so the door isn't closed, but not resolved or rendered — agreed early in the design conversation, not dropped for lack of time.
- **Table sizing clamp removed outright, not adjusted.** The user's explicit instruction: "neither validation is correct... get rid of it," having been shown no valid reason to keep either the ceiling or the floor. Led directly to a new standing principle (Architecture, "Validate only where designed") that validation/clamping is an architectural decision requiring sign-off, not a default to add defensively.
- **PDF image-quality limitation accepted, not chased further, for now.** After confirming DPI increases, `autoCompressPictures`, and a `SaveAs` swap don't resolve it, and every alternative pathway carries its own disqualifying cost (licensing, lost hyperlinks/text, a second rendering engine's fidelity risk), the user's own call: current output is adequate for this stage of development; PowerPoint may need revisiting as the reporting middleware if this becomes a bigger issue later, but that's not an active workstream.


## Session — SVG Rendering Methodology Rollout

- **Every Base Chart and Base Table renders as SVG, not PNG, going forward.** Chosen over raster because raster pictures pixellate on screen and on PDF export regardless of DPI or PowerPoint's own compression settings, while PowerPoint's native content stays crisp at any zoom; SVG, being vector, has no such ceiling. See Architecture Decision 27.
- **Font standard is Calibri**, set via `matplotlib.rcParams["font.family"]`, baked into vector outlines (`svg.fonttype` left at its own default, `"path"`) rather than kept as live, selectable text (`"none"`). The live-text alternative was deliberately rejected: it does not make chart/table text genuinely searchable or selectable in PowerPoint or either PDF export pathway tested, and introduces character-positioning corruption in the exported PDF specifically -- a real cost with no corresponding benefit.
- **Accepted, not further pursued: chart/table text remains unsearchable/unselectable in PowerPoint and the exported PDF.** Confirmed structural (PowerPoint treats an embedded SVG's contents as opaque to its own Find and the PDF's text layer, regardless of `svg.fonttype`) rather than a tunable setting -- genuine searchable table text, if ever required, would need a fundamentally different approach (e.g. native PowerPoint text boxes over a vector/graphic background), not a setting change to this mechanism.
- **Accepted, not further pursued: unhinted vector text renders thin vertical strokes fractionally too heavy in some PDF viewers (confirmed in Adobe Reader) at low zoom.** A known, inherent consequence of `svg.fonttype="path"` discarding font hinting metadata; disappears at higher zoom or in print. Cosmetic, not treated as a defect to keep chasing.
- **PDF export (`save_pdf`) reverted to `ExportAsFixedFormat` with default settings, at the user's explicit request**, superseding the `SaveAs(path, 32)` mechanism a prior session had settled on (Decision 26). The prior mechanism's own rationale (raster image downsampling under `ExportAsFixedFormat`'s defaults) still stands for genuine raster content (`insert_picture`) -- this reversion was made specifically because it made no difference to the SVG-text-positioning problem under investigation this session, not because the original raster finding was found to be wrong.
- **`table_ledger`'s explicit `fontfamily="serif"` override was deliberately left as-is, not switched to Calibri** -- read as an intentional per-table aesthetic choice (its own ledger/accounting look), not something this session's font-default change was meant to touch.
