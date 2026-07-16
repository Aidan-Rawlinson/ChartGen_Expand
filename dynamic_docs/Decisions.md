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
