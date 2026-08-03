<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE -- READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the six governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base -- which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously -- during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in -- expect churn, don't resist it.
>
> **Standing rule (confirmed by the user, still in force): Base Charts and Base Tables are never documented in the governed docs -- not their existence, not their internals.** Only a genuine core-system-level change belongs there. Do not log a new Base Chart/Table's existence "for completeness."

## Status: A short, focused session -- one side-quest (a markdown reference doc on the Indicators toolkit's own endpoints, for another Claude's use, no code changed) and one real feature: the Custom Tables download bundle can now optionally include full detail for every embedded chart-component cell's own Chart Store entry, closing a real gap the previous session's table-export work had left open. Static docs updated and re-uploaded as of this close-down.

### This session's work

**Indicators toolkit endpoint reference (no code change).** Produced, at the user's request, a dense markdown reference document (for consumption by another Claude instance, not a person) covering `core/acquisition/toolkit_indicators/`: the URL shape and `url_parser.parse_url` field extraction, all three `api_client.py` endpoints and what each is keyed by, `fetch.py`'s per-project caching of `/projects/{id}/submissions`, and `transformers.transform`'s period-visibility filtering and stats recomputation. Purely informational -- verified against the actual current code, nothing changed.

**Custom Tables bundle can now optionally export embedded chart detail (Architecture Decision 35).** A `{Cn}` chart-component cell was previously opaque to a table's own bundle -- the table function never touches the chart it names, so neither did the bundle. A new checkbox in the Output Tables tab's Custom Tables section ("Tick here to export charts", off by default) makes `build_bundle` scan `content` for every distinct chart-component marker and, for each one still resolvable in `chart_store_rows`, append that entry's own settings, complete rendering source, and live `population_layers` -- plus one explanatory section up front on how the two-step render-then-composite relationship works, so the whole table can be rebuilt, embedded charts included, from that one document alone.

**`chart_store.py` gained `resolve_chart_store_population_layers`** -- the cache-load/cut/population-default-fallback/layer-build pipeline the bundle needed, extracted rather than duplicated a third time; `output_tables_tab.py`'s own Preview chart-in-cell splice was refactored to call this shared function too, removing its own previous copy of the same logic.

**Real bug found and fixed during this same build, before it ever shipped to the user uncorrected:** the bundle's own marker-scanning regex initially required the text after `{C` to look like the auto-generated base-36 id shape (`[0-9a-z]+`). Confirmed wrong against the user's own real table, which uses hand-typed ids like `{CH1}`/`{CV1}` -- every Base Table's own `_chart_cell_id` check has always been far more permissive (only checks the `{`/`}`/leading-`C` shape, nothing about what follows), so those cells' charts were silently missing from the exported bundle even though the table itself renders them correctly. Fixed to match `_chart_cell_id`'s own real rule exactly (`^\{(C.*)\}$`) rather than an assumed-but-wrong stricter one.

### Known gaps / not yet done (all carried forward, none touched this session)

- **The same `cell.value`-without-`number_format` gap may exist in Stat Tags', Chart Store's, and the Running Order's own Excel readers** -- only the Output Table content path has been fixed; the others are an un-investigated, live risk of the same failure mode.
- **Base Table trim (from an earlier session) is still a potential breaking change for any existing workfile using one of the eight removed styles** -- not confirmed clear with the user.
- **SVG transparent backgrounds for tables** -- still deferred, case-by-case, per the user's own earlier plan.
- **A residual "pixel or two too low" vertical offset in `table_cardtile`'s chart-cell placement** -- still parked, not investigated.
- **Governed docs re-upload** -- done. User confirmed re-upload to Project Files immediately before this close-down.
