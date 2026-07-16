<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the six governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.
>
> Note: the Maintenance Guide now governs **five** documents, not six — "Refactoring Issues" was scrubbed this session (it misdescribed new-functionality work as refactoring); deferred/known gaps now live as Notes on the relevant Feature List row instead.

## Development Plan — Multi-project / Multi-database Expansion

Steps agreed with the user, each independently buildable and testable. Renumbered this session — the four steps completed (generic URL table, multi-project/same-database, streamlined New Workfile flow, tidy) are removed; only the remaining, not-yet-started work is listed.

1. Second database (new timeseries data shape, new Base Charts, credential requirement, organisation ID collision handling) — *Not started*
2. Credentials (URL-to-database triage, generic credentials box on Imports tab, fail-soft on missing credentials) — *Not started*
3. Yellow-box parity for second database (route through same triage/credential logic as manually-entered URLs) — *Not started*

## Status: In progress — multi-project/same-database (formerly Step 2) and New Workfile streamlining (formerly Step 6) built and live-tested; doc catch-up (formerly Step 7) complete

### What works (built this session)

- **Multi-table population model** — `WorkfileState.tables`/`table_order` replace the old single `units.csv`; `.cgw` storage generalised to `workfile_config/tables/{table_name}.csv`, any number of them. File version bumped to 0.0.3 (hard-refuses 0.0.2 and earlier).
- **`nhs_organisations` + `submissions_{year}_{project_id}` tables**, both on the shared spine (`unit_id`, `unit_code`, `unit_name`, `soft_parents`, `Region()`). `nhs_organisations` filtered to only organisations actually referenced by a submission.
- **`soft_parents` relationship model** (`core/shared/infrastructure/soft_parents.py`) — child-side-only recording, one hop, both directions: `format_soft_parents`, `parse_soft_parents`, `resolve_related_rows`, `resolve_referencing_rows`, `resolve_all_related_rows`, `resolve_full_unit_set`.
- **Automatic population-table creation** — `ensure_population_tables` (in `acquisition/toolkit_nhs/population_tables.py`, not `workfile.setup`) triggers inside `fetch.py`, per chart, the first time a project/year is seen; no user-facing "add project" action exists. `add_project_tables` merges `nhs_organisations` across projects (append by `unit_id`, no overwrite, no re-resolution of `Region()` needed since it's a per-organisation API value).
- **`create_new_workfile` / population tables fully divorced** — workfile creation (`workfile/setup/new_workfile.py`) has zero knowledge that population tables exist.
- **Populations tab** (reorderable ▲/▼, collapsible, master = whichever table sits on top, ★ MASTER badge) and **Reporting unit selection tab** (Full Unit(s) table, reporting unit's own row bolded).
- **`population_table` field** stamped on every data shape at fetch time. `insert_chart` and the Charts tab preview resolve each chart's correct table and correct selected unit(s) (which can legitimately be more than one) via `AssemblyContext.full_unit_set`, rather than assuming every chart's population is the master table.
- **Chart titles removed** from all 17 Base Charts (reports and preview alike). Bead-string plot de-duplicates visually across tiers (Selected suppressed from broader tiers it's also in) — statistics unaffected.
- **New Workfile flow streamlined** — collects a short description (shown next to "ChartGen" in the app header, Coral Red `#FF4B4B`) instead of year/project/name; single native Save dialog (`pick_save_file`) replaces folder-picker + name box for both New Workfile and Save As; the app's own overwrite-confirmation step removed (the OS dialog already handles it). Year/project_id/project_name no longer stored at the workfile-settings level at all.
- **Charts tab** reads the live `set_default_populations` value off the Running Order for its preview default (acknowledged stopgap, see gaps below).
- **All governed docs current** — Architecture, Functional Spec, Feature List, Glossary all updated to match; Primer untouched (edit-locked).

### Known gaps / not yet done

- One-hop-only relationship resolution is deliberate for now — a genuine multi-level chain (Country→Region→ICB→Organisation→Submission→Ward) isn't walked automatically. Revisit once more than two tables/deeper chains are actually needed.
- Charts tab's `set_default_populations` lookup reads one Running Order row's value directly — a stopgap, not a general settings-reading mechanism.
- `nhs_organisations`' merge assumes `Region()` (and any future peer-group column) is a value handed to us per-organisation by the API, not computed from the full table. Would need revisiting if that stopped being true.
- Installer script bumped to `0.0.3` this session; the user was walked through compiling/testing/publishing, but completion (a real compiled `0.0.3` installer copied to the SharePoint release location) was not confirmed back before Close-down.
