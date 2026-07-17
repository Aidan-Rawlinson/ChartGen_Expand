<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Status: Charts sheet rebuilt as a full two-way sync with the Running Order (was previously a preview-only stopgap); governed docs updated to match. Organisation-identity mismatch work remains parked, pending a data extract the user now has in hand for next session.

### What works (built this session)

- **Charts sheet is now a genuine two-way sync with the Running Order**, replacing the old preview-only tab:
  - Two entry points, always convertible into each other: load an existing `insert_chart` Running Order row (bound mode), or load a cached dataset directly (free-play, no row bound).
  - Round-trip fields (`chart_type_ref`, `cache_file`, `populations`, `width_emu`, `height_emu`) governed by a single maintained list, `CHART_SANDBOX_FIELDS` (`running_order/schema.py`) — extending the sync later is a one-line addition there, not a rework.
  - Save-back via three actions: Overwrite selected row, Insert above, Insert below — new module `running_order/row_ops.py` (`overwrite_row_fields`, `insert_new_row`, `renumber_row_ids`).
  - Rows referenced by `row_id`, not list position or label — stable across an Overwrite; sandbox state referencing a row is cleared after every save so an Insert's renumbering can't leave a stale reference.
  - Sizing is authored as a percentage of the PowerPoint page's shorter dimension, not raw EMU — new module `core/shared/infrastructure/page_sizing.py` (`percent_to_emu`, `emu_to_percent`, `get_page_size_emu`, `has_known_template_page_size`, standard page-size presets). Real page size is captured once at template processing (`import_flow.process_template` now writes `template_page_width_emu`/`template_page_height_emu` into workfile settings); a manual dropdown stands in before any template has been processed.
  - The Charts tab's old stopgap — reading one Running Order row's `populations` value directly to approximate a preview — is gone. It now does real `build_population_layers` resolution, the same mechanism `insert_chart` uses at batch time.
  - Shape-mismatch handling: swapping the loaded dataset to a different data shape while a row is bound doesn't unbind the row, but warns and re-filters chart type options.
  - Placeholder dropdown entries ("- Running order line -", "- Chart list -", "- Select target row -") are genuine string options in each dropdown's own list, not Python `None` — this also fixed a real Streamlit bug where a `None`-based sentinel, once pre-set into `session_state`, triggered Streamlit's own built-in "Choose an option" placeholder instead of our `format_func` text.
  - Selecting either "Select Chart" placeholder after something was already loaded triggers a full sandbox reset (same as the reset button), via transition-detection so it doesn't loop on first load.
- **Streamlit layout**, native-only (no CSS): title + reset icon at the top; left rail (~17.5% width) holds every control that saves to the Running Order, in expanders ordered as Select Chart (open) → Select Visualisation (auto-expands while no chart type chosen) → Populations → Sizing → Save to Running Order → Zoom (the one expander whose control saves nothing, kept last for that reason).
- **Governed docs updated to match** (Primer untouched, per its edit lock — nothing here touched design intent): Functional Spec (§9.3 Charts Sheet Round-Trip, §9.4 Page Size Capture, §3.2 tab purpose, §10.6 cross-reference), Architecture (package tree + module table for `row_ops.py`/`page_sizing.py`, `settings.csv` key list, new Decision 11), Feature List (`set_default_populations` stopgap note resolved, two new Complete rows), Glossary (two new Cluster 8 terms).

### Known gaps / not yet done (unchanged from last session, still parked)

- **Organisation-identity mismatch between the two toolkits.** Still believed real, still unconfirmed against live data, still nothing built. **User now has a CSV extract in hand for next session** — see Next_Session.
- The `organisationCode`/`organisationName` field-name bug in `extract_submissions` (unverified guessed keys) — bundled into the same future fix.
- TimeSeries period cutting (single period/range) — not built.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) — not built.
- One-hop-only `soft_parents` resolution — deliberate scope boundary, not a bug.
- `format_modifier` retrofit — CategoricalCompositional-only gap, unchanged.
- The three TimeSeries charts (from last session) still haven't had a real batch-run test pass into a live template.
- The new Charts sheet round-trip likewise hasn't been tested against a live workfile/batch run — built and reasoned through this session, not yet exercised end-to-end by the user.

### Resolved / dropped this session

- **Charts tab's `set_default_populations` stopgap** — resolved. No longer reads a Running Order row directly; does real population resolution.
- **Front-end iteration** (this session's early phase, once the round-trip mechanism was built) — layout, wording, sizing tweaks all closed out; user confirmed satisfied with the current state.

### Noted, not yet actioned

- **Placeholder removal alongside yellow-box removal.** Cleaned-template production strips yellow textboxes but leaves the placeholder itself in place; an empty placeholder is still visible in the PowerPoint editing view (though it doesn't render at output). User asked for this to be logged, not built, this session.
