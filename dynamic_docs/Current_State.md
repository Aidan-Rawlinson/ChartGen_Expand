<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE -- READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the six governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base -- which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously -- during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in -- expect churn, don't resist it.
>
> **Standing rule (confirmed by the user, still in force): Base Charts and Base Tables are never documented in the governed docs -- not their existence, not their internals.** Only a genuine core-system-level change belongs there. Do not log a new Base Chart/Table's existence "for completeness." This extends to memory and session notes too, not just governed docs -- a Base Chart's own implementation detail (internal assumptions, data-handling quirks) is never worth recording anywhere; it's outside the system boundary, the same way an Excel custom chart template's own internals are.
>
> **Standing rule: avoid unasked-for defensive coding.** Silent clamps, silent drops-on-mismatch, silent fallback defaults -- an earlier session found and fixed two real bugs caused by exactly this pattern (a UI silently discarding a mismatched stored value instead of surfacing the mismatch; an Excel reader treating "no label" as "no value"). When a value might not resolve, let it fail visibly or flag it, rather than pre-emptively guarding against it without being asked.
>
> **Standing rule: a value the person actually picked or typed is never silently rewritten, reconstructed, or re-derived later** (on export, on re-save, etc.). If something needs deriving from live data, it happens once, at the point of actual use, not retroactively applied to what's already stored.

## Status: Two small, self-contained UI additions this session (Project Folder button; Export Picture button from the prior session remains in place). No changes to data model, transformers, or Running Order behaviour. One substantial exploratory exercise (SVG font handling / a 4x-oversize-then-shrink scaling bodge) was built, tested, and then fully removed at the user's own request -- no trace of it remains in the codebase or these docs.

### This session's work

**"Project Folder" button added to the sidebar (`sidebar.py`).** Sits at the very bottom, below the Version/Sign Out expander. Opens the folder containing the currently open workfile in Windows Explorer via `os.startfile`, disabled when no workfile is open. Only meaningful with a workfile open, since there's no "project folder" concept otherwise. `os.startfile` is safe specifically because ChartGen runs locally, one user per machine (`run_chartgen.bat`) -- it would open Explorer on the server instead of the user's own PC under a hosted, multi-user deployment, which isn't today's architecture but is worth remembering if that ever changes.

Feature List updated with one new row for this (sidebar/workfile-operations section) -- no Architecture Decision judged necessary, same reasoning as Export Picture: a new, independent action, no change to any existing mechanism or contract.

**Exploratory work, fully reverted, not recorded further:** at the user's request, two CI-chart variants (`line_ci_full2`, `column_ci_full2` -- SVG text as real `<text>` rather than glyph outlines) and one bodge variant (`line_ci_full3` -- rendered at 4x size internally, then physically shrunk back down on insertion, to test a font-scaling technique) were built, wired into the registry/chart_type_map, tested, and then deleted along with every trace of their wiring (registry entries, chart_type_map rows, and a temporary special-case in `assembly_engine.insert_chart`) at the user's own request. Codebase is back to exactly its pre-exercise state for anything touched by that work. Nothing about SVG font-embedding behaviour or the draw-big-then-shrink scaling technique itself needs recording here -- it was discussed and demonstrated, not adopted.

### Known gaps / not yet done (carried forward, none touched this session)

- The radar-cycling multi-submission-per-organisation limitation is still unverified against a real case.
- 16 SPs from an earlier session's full mapping still have no transformer written.
- PairedSurveyData still has no transformer, no Base Chart, and no Stat Tags (`reference_ids.py`) integration.
- Per-unit `metadata` on the shared `Unit` base class is designed but not coded -- needed before cross-service transformers can be built.
- The same `cell.value`-without-`number_format` gap fixed for Output Table content (Architecture Decision 34) may still exist in the Stat Tags, Chart Store, and Running Order Excel readers -- not investigated.
- Any Running Order `.xlsx` exported before the period-field storage rework (several sessions back) should be re-exported fresh rather than reused.
- Base Table trim (from an earlier session) is still an unconfirmed, potential breaking change for any existing workfile using one of the eight removed styles.
- SVG transparent backgrounds for Output Tables -- still deferred, case-by-case.
- A residual "pixel or two too low" vertical offset in `table_cardtile`'s chart-cell placement -- still parked.
- A larger, unscoped feature raised in conversation some sessions back: conditional per-unit slide deletion plus a matching index-page regeneration. Needs its own dedicated design session.
- Worth a visual check, not a design task: with `metric_periods` no longer raising on an unresolvable id, a metric with no data now flows through to whichever Base Chart renders it -- worth looking at how a couple of real charts actually handle that, still not done.
- If SVG-text-as-real-text (rather than glyph outlines) is ever wanted for a production chart, not just testing: font embedding into the exported PDF is not automatic and not yet verified either way -- see this session's chat for the reasoning (PowerPoint's own "embed fonts" setting doesn't cover text inside an embedded SVG image; the actual PDF would need checking with a font inspector such as `pdffonts` or Acrobat's Document Properties before trusting it on another machine).
</content>
