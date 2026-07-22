<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Status: This session was functionality work — a small feature request that led to finding and removing a genuinely dead Running Order field. Chart-type default-population now works correctly (moved to the right trigger point after an initial wrong placement); the Running Order's `placeholder` column has been removed system-wide, code and docs, having been found to serve no live purpose and to carry a latent key-collision risk. Prototype-sharing plan (quick-start guide, sample templates, installer check) is untouched this session — still open, see below.

### What works (built/fixed this session)

- **Chart type default-population on `insert_chart` rows.** Once Fetch resolves a chart's `shape_type`, any Running Order row still holding a blank `chart_type_ref` is silently backfilled with the first valid chart type for that shape (`chart_type_map.csv`'s own row order). Never overwrites a `chart_type_ref` that's already set (manual edit, or a prior backfill). No user-facing message.
  - **First attempt was wrong and was corrected mid-session:** initially built into `generate_from_template` (Running Order generation time), on the reasoning that shape might already be known on a structural-re-upload-after-fetch scenario. In practice, Running Order generation *always* precedes Fetch — there's no code path where it doesn't — so the shape is never known at that point and the logic never fired. User caught this via live testing (processed a template, ran Fetch, chart type stayed blank).
  - **Fix:** the default-lookup logic (`generation.py`: `default_chart_type_ref_for_shape`, `backfill_default_chart_types`) is now also called from a new `backfill_chart_types_after_fetch` in `import_flow.py`, invoked once at the end of the Fetch action (`imports_tab.py`), silently, after `fetch_all()` returns.
  - Documented in Functional Spec §7.1.

- **Running Order `placeholder` column removed entirely — system-wide.** Traced through the full lifecycle and confirmed it was never a live reference: the PowerPoint placeholder object it named is deleted from the cleaned template the moment it's matched (Decision 13/§6.4), and every execution path (`assembly_engine.py`, `insert_picture.py`, `insert_from_excel.py`) places content purely by `left_emu`/`top_emu`/`width_emu`/`height_emu` + `slide_index` — never by name lookup. Its only remaining uses were: (a) a UI caption/table column (cosmetic), and (b) a dict key on `ctx.autotable_stats` inside `insert_chart` — which turned out to be a live bug risk, since placeholder names are only unique **per slide**, not across the whole Running Order, so two slides sharing a placeholder name (e.g. both called "Chart 1") would have silently overwritten each other's autotable stats once Autotables ship. Fixed by re-keying `ctx.autotable_stats` on `row_id` instead (Architecture Decision 11's row identity).
  - Also removed a genuinely dead result message in `insert_chart` (`ok_result` text naming the placeholder) — confirmed via code trace that `batch_process.py`'s `run_batch` only ever surfaces a **per-unit** summary log (`log_rows`), never the per-row `ctx.log` list; the per-row message was built and discarded on every single chart insert, for every report, always. `empty_placeholder`'s equivalent message was left in place (simplified to reference `row_id` instead of the removed field) per explicit user instruction — the general "per-row `ctx.log` is built but never surfaced anywhere" question was raised and deliberately left for a later session, not fixed now.
  - Removed from: `schema.py` (`COLUMNS`), `generation.py` (row templates + docstring), `xlsx_writer.py` (column-width map — header/data writing was already schema-driven), `row_ops.py` (stale comment), `assembly_engine.py` (`insert_chart`, `empty_placeholder`), `running_order_tab.py` (edit-dialog caption, overview table column). `xlsx_reader.py` needed no change — already fully schema-driven.
  - Documented in Architecture (Running Order column schema table), Functional Spec (§6.2, §6.3, §9.1, §9.2), and Glossary (*Placeholder*, *Free-floating yellow box*).

- **Running Order overview table — minor formatting only, not documented in the governed docs per user instruction.** `#`, `On`, and `Slide` columns set to Streamlit's `column_config` minimum named width preset (`"small"`, 75px).

### Known gaps / not yet done (carried forward)

- **Not yet re-tested live by the user** after the chart-type-backfill fix and the placeholder-column removal — worth confirming a template→Fetch→Running Order pass shows chart types populating correctly, and that nothing else relied on the removed field, before treating either as fully closed.
- Prototype-sharing plan (from the previous session) is still open and untouched this session:
  - Quick-start guide — not started.
  - Sample PowerPoint templates — user's own task, status unknown.
  - Installer check on colleague's machine — not started.
  - Known-issues briefing explicitly out of scope, by user call.
- Guidance PDF and its build script exist only on SharePoint / a prior session's sandbox — not saved into the project folder. Any future content update means rebuilding from scratch.
- Sidebar divider line — abandoned, root cause never identified. Plain spacer divs in place. Don't relitigate without a genuinely different technique.
- Sidebar/main CSS spacing — accepted as "good enough," not chased further.
- Sidebar dirty marker (●) for unsaved changes — dropped, never restored, not raised again since. Treat as accepted unless the user brings it up.
- Process-restart gotcha still applies: the `.bat`'s background Streamlit server survives closing the browser tab. Flag early in any UI/CSS session where changes appear not to take effect.
- Table-wide `chart_type_ref`/`metric_periods` validation on Excel upload — still deferred, needs its own scoping conversation.
- Population-table Excel edits still unvalidated (dangling `soft_parents` possible) — same deferral.
- No live batch-run test yet for Period Range / Convert Periods to Metrics, TimeSeries charts, or the Charts sheet round-trip more broadly, against a real template.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) — not built.
- One-hop-only `soft_parents` resolution — deliberate scope boundary, not a bug.

### Resolved / dropped this session

- Chart-type default-population — working, moved to the correct trigger point (post-Fetch backfill).
- Running Order `placeholder` column and every writer/reader of it — removed, code and docs.
- `ctx.autotable_stats` keying — fixed from placeholder name (collision-prone) to `row_id` (safe).

### Noted, not yet actioned

- The per-row `ctx.log` mechanism (built inside every Running Order function's `ok_result`/`err_result`, appended in `run_running_order`) is confirmed to have **no consumer anywhere** — `batch_process.py` only extracts the first error message on failure, everything else is discarded, even for Run Selected against a single unit. Left as-is this session at the user's request ("let's leave that for the moment"). Worth a dedicated conversation later: either give it a real consumer, or strip the now-pointless message-building out of every Running Order function.
