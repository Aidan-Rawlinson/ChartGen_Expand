<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE -- READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Migration to Claude Code.** Feature work is paused. The project is moving from Claude Chat to Claude Code, and the active work is context and structure only -- markdown files, docstrings, comments, file locations, import paths. See `Claude_Code_Migration_Plan.md` in the project root. That plan supersedes this file's own role: it is the working document, and `dynamic_docs/` is scheduled for deletion at the end of its Stage 2.
>
> **Standing rule: no change to the function of code without explicit permission, for the duration of the migration.** Path and import updates arising from the Stage 1 restructure are in scope. Defects found in passing are raised, not fixed.
>
> **Standing rule: Base Charts and Base Tables are never documented in the governed docs** -- not their existence, not their internals. The shared rendering mechanism they participate in (SVG scaling factor, `svg.fonttype`, the `TEXT_SCALE`/`CHART_RENDER_SCALE` convention) is a genuine system-level fact and is the exception.
>
> **Standing rule: check the actual registry/file listing before trusting a stale count.** This session found three live examples: `shapes/common.py` says three canonical shapes, `base_charts/registry.py` says four, there are five; and prior session notes recorded 23 Base Charts when `CHART_REGISTRY` holds 33.
>
> **Standing rule: avoid unasked-for defensive coding.** Silent clamps, silent drops-on-mismatch, silent fallback defaults. Let a value fail visibly or flag it.
>
> **Standing rule: a value the person actually picked or typed is never silently rewritten, reconstructed, or re-derived later.**

## Status: Design-only session. No code changed. A full review of the codebase and the six governed documents produced an agreed five-stage migration plan, written to `Claude_Code_Migration_Plan.md` in the project root. Nothing from the plan has been executed.

### This session's work

Reviewed the complete package tree under `code_base/ChartGen/core`, the six governed documents, and a structured sample of docstrings across every layer, to plan the move from Claude Chat to Claude Code.

**Findings.** The six documents total 2,179 lines; `ChartGen_Architecture.md` alone is 1,025 lines, mostly a 50-entry decision ledger written as narrative. Across the codebase, 32 occurrences of "Decision N" reference that ledger from roughly 25 modules. Around 45 occurrences of session-historical language ("this session", "moved here", "previously", "renamed from"). Three confirmed cases of the explanatory layer having gone stale against the code, listed in the standing rule above. `assembly_engine.py` references a `Restructure_Plan.md` open item that no longer exists in the project folder.

**Structural review for Stage 1.** The top-level importable package is `core`, not `ChartGen`. `venv/` and `installer/` both sit inside the application folder. `run_chartgen.bat` installs a hardcoded package list and never reads `requirements.txt`, so that file is currently inert. No `tests/` anywhere in the tree.

**Outcome.** A five-stage plan, agreed in full: restructure, documents, `CLAUDE.md` files, docstrings across the system layer, docstrings across Base Charts and Base Tables. Lead surface marked per stage. Stage 1 is ready to hand to Claude Code.

### Known gaps / not yet done

Feature-work items below are all carried forward untouched and stay parked for the duration of the migration.

- Glossary's Base Table count is still stale -- now folded into the migration as a correction to make when `docs/GLOSSARY.md` is produced in Stage 2.
- Whether real `<text>` is genuinely searchable in PowerPoint's Find or the PDF text layer has not been verified.
- The radar-cycling multi-submission-per-organisation limitation is still unverified against a real case.
- 16 SPs from an earlier session's full mapping still have no transformer written.
- PairedSurveyData still has no transformer, no Base Chart, and no Stat Tags (`reference_ids.py`) integration.
- Per-unit `metadata` on the shared `Unit` base class is designed but not coded.
- The `cell.value`-without-`number_format` gap may still exist in the Stat Tags, Chart Store, and Running Order Excel readers.
- Any Running Order `.xlsx` exported before the period-field storage rework should be re-exported fresh.
- SVG transparent backgrounds for Output Tables -- deferred, case-by-case.
- A residual vertical offset in `table_cardtile`'s chart-cell placement -- parked.
- Conditional per-unit slide deletion plus index-page regeneration -- needs its own design session.
- With `metric_periods` no longer raising on an unresolvable id, a metric with no data flows through to whichever Base Chart renders it -- worth a visual check on real charts.
