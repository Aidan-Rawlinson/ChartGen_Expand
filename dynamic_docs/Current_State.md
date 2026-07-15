<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the six governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Development Plan — Multi-project / Multi-database Expansion

Steps agreed with the user, each independently buildable and testable. Work proceeds a couple of steps at a time, without a full Close-down between every step. Update each step's status as work progresses; don't wait for a full Close-down to mark progress here.

1. Reinstate generic URL table (Excel round-trip, matching the Running Order's xlsx export/import pattern) — **Done, live-tested**
2. Multi-project, same database (submissions/organisations expansion, master table concept) — *Not started*
3. Second database (new timeseries data shape, new Base Charts, credential requirement, organisation ID collision handling) — *Not started*
4. Credentials (URL-to-database triage, generic credentials box on Import tab, fail-soft on missing credentials) — *Not started*
5. Yellow-box parity for second database (route through same triage/credential logic as manually-entered URLs) — *Not started*
6. Streamline New Workfile flow (long name + file picker, replacing project/year-first setup and folder pickers on Save/Save As) — *Not started*
7. Tidy (file version id bump if needed, doc catch-up: Glossary Project definition, Primer population description, Feature List rows across all steps)

## Status: In progress — Step 1 (manifest table) built, live-tested, and documented

This session deleted the stale Architecture Decision 9, agreed and recorded the seven-step expansion plan above, then built Step 1 end to end.

### What works (built this session)

- **Manifest table** (`data_cache/manifest.csv`) — the chart URL table and canonical index of every chart, one row per URL. Replaces both `workfile_config/urls.csv` and `data_cache/manifest.json` (both deleted). Columns: chart_ref, hex_id, url, chart_title, database, project_id, service_id, year, shape_type, source, deleted, added_at, data_updated_at. Fetch-populated cells hold `...` until first fetch. Schema owned by `workfile_file.py` (`MANIFEST_FIELDNAMES`), which also owns `generate_hex_id`, `new_manifest_row`, `renumber_chart_refs`.
- **Hex id identity** — 5-digit uppercase hex, unique including deleted rows, never reused. Names the cache file (`{hex_id}.json`, replacing `{tier}_{group}_{option}.json`) and is the Excel round-trip identity. chart_ref (`Chart_0001` style) is display-only, renumbered across non-deleted rows on every change.
- **Deleted-row semantics** — deleted rows stay in manifest.csv with hex_id reserved and cached data kept; hidden from UI, excluded from Excel export, skipped by fetch. Template re-upload containing a deleted URL resurrects the row under its original hex_id.
- **Decoupled fetch** — template processing populates the table and generates the Running Order only (cache_file assigned as `{hex_id}.json` pre-fetch; chart-type dropdowns unconstrained until data arrives). The Imports tab's Fetch button is the single fetch: full refresh of all non-deleted rows, populating title/project/service/year/shape per row.
- **Excel round-trip** — new package `core/acquisition/manifest_table/` (xlsx_writer, xlsx_reader). Export: Running Order palette, url column editable-green, system columns grey, chart_ref and deleted excluded, hex_id carried as identity, 300 blank formatted input rows appended. Import: blank hex_id + URL = new Direct Input row; missing hex_id = deleted; unknown hex_id rejected. `apply_manifest_import` is the single merge routine.
- **Imports tab reworked** — three sections: template (no fetch), read-only chart URL table (`st.dataframe`; editing via Excel only — an editable `st.data_editor` version was built then removed at the user's request), Excel download/upload (upload behind a toggle button matching the Running Order tab's pattern), single Fetch section.
- **File version 0.0.2** (software id also 0.0.2) — 0.0.1 workfiles hard-refuse on Open, per the no-migration model.
- Live-tested by the user end to end, including output generation. One mid-test issue (stale Running Order referencing old cache names from a hot-reloaded process) resolved by fresh relaunch + template re-process.

### Documentation (all six governed docs current as of this session)

- Architecture: Decision 9 deleted; §4 tree/table (manifest_table package, import_flow description); §5 .cgw layout, manifest.csv column schema table added, CSV-vs-JSON note; §6 WorkfileState (`manifest_rows` replaces `urls`/`manifest`).
- Functional Spec: §3.2 Imports row; §6.3 extraction paragraph (no auto-fetch); §7.1 rewritten (two entry routes, single explicit fetch); §7.3 Data Cache.
- Feature List: Part 3 — chart URL table and direct URL entry rows added (Complete); API route note updated.
- Glossary: Data Cache updated; Chart ref, Hex id, Manifest table entries added.
- Mirror copies in static_docs_mirror/project_files are current; user re-uploaded to Project Files at Close-down.

### Known gaps / not yet done

- Update-mechanism gaps carried from last session: the real "update available" path is untested (only "up to date" and graceful-failure exercised); version-bump discipline is manual.
- Pre-existing Glossary stale cross-references flagged, not fixed: `.cgw` entry points to Architecture §4 and WorkfileState entry to §5, for content now in §5 and §6 respectively.
- Software id 0.0.2 has not been released through the installer pipeline — the SharePoint release copy is still the 0.0.1 build.
