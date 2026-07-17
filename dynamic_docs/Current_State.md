<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Development Plan — Multi-project / Multi-database Expansion (closed out)

All three original steps, plus the follow-on chart-rendering work, are complete:

1. Second database (new timeseries data shape, new toolkit package, organisation ID collision handling) — *Done*
2. Credentials (single shared credential box relocated to Config tab, URL-to-database triage, fail-soft on missing credentials) — *Done*
3. Yellow-box parity for second database (both entry routes resolve database via the same triage function) — *Done*
4. TimeSeries chart rendering (three Base Chart types, wired end-to-end) — *Done, this session*

This plan is retired. Work from here is unplanned/ad-hoc — see Status and Next_Session for the live thread (organisation-identity mismatch between the two toolkits).

## Status: TimeSeries charting built end-to-end (three chart types); Primer maturity-statement gap resolved; organisation-identity mismatch between the two toolkits now believed real, not just a documented assumption

### What works (built this session)

- **Maturity-statement anchor sentence added to the Primer** (Section 1, user-approved specific edit — Primer is edit-locked). States ChartGen is under active development, built by a single developer, and points to the Feature List as the authority on built-vs-planned. Resolves a gap flagged across several previous sessions.
- **TimeSeries wired into the shared dispatch machinery.** `shapes/dispatch.py`'s `filter_shape`/`autotable_stats` now route to `filter_time_series`/`time_series_autotable_stats` (both already existed from last session, just never called). `population_layers.py`'s `_get_shape_units` now handles TimeSeries the same way as the other two multi-metric shapes (`metrics[0].units`). Confirmed the rest of the pipeline — `insert_chart`, `build_population_layers`'s scope/token resolution, EMU sizing, image insertion, the Charts tab preview — was already shape-agnostic and needed no change at all.
- **New `core/output_generation/execution/charts/base_charts/timeseries.py`** — three Base Chart functions, all following the box_whisker/violin_plot convention (`population_layers[0]` is always the scope; subsequent layers are highlighted on top):
  - `period_line_chart` — population mean + IQR band, Selected/peer lines on top.
  - `median_comparison_linechart` — median per layer instead of mean; `Selected` charts the actual unit value(s) rather than a median (a median of one unit's own values isn't a meaningful statistic the way it is for a wider population).
  - `full_lines_linechart` — every individual unit in the scope drawn as a thin, low-alpha grey line (confirmed against a quick round of design research as the standard "spaghetti plot" technique — diminish the background with genuine transparency, not just a lighter flat colour, so overlapping density shows through); every subsequent layer's own unit line(s) drawn on top, highlighted.
- **Design-pass fix applied to both newer charts:** proxy-artist legend entries (empty `ax.plot([], [])` calls) so a population layer holding more than one unit — the documented one-to-many `Selected` case, or a multi-unit peer group — gets exactly one legend entry, not one duplicate per unit.
- **Registered everywhere needed:** `registry.py` (`CHART_REGISTRY`), `chart_type_map.csv` (3 new TimeSeries rows). Confirmed the Charts tab and Running Order dropdown both pick these up automatically with no changes — already shape-agnostic.
- New shared constant `GREY_LIGHT` added to `base_charts/shared.py` for the spaghetti-plot background lines.
- Stale docstrings corrected in `shapes/__init__.py` and `base_charts/__init__.py` — both previously stated TimeSeries/the fourth shape wasn't wired in yet; now false, now fixed.
- **All governed docs updated to match:** Feature List (chart counts 17→20, new TimeSeries rows for chart rendering, period-cutting gap, and reporting-unit highlighting), Functional Spec (§8.3, §10.1, §10.2 table), Architecture (package tree, two prose rows, removed the stale "TimeSeries not wired in yet" sentence). Glossary needed no changes. Primer's one-sentence addition as above.

### Known gaps / not yet done

- **Organisation-identity mismatch between the two toolkits is now believed real, not just a documented assumption.** User strongly suspects Indicators `organisation_id` does NOT match `nhs_organisations`' `unit_id` space. If confirmed, the current `soft_parents` link (`nhs_organisations:{organisation_id}`, Decision 10) is wrong at the root, not a display-only issue. User's explicit instruction: a lookup table will likely need to be uploaded into the tool, applied at the earliest point (before the `soft_parents` link is made), not patched on afterward. Nothing built yet — deliberately deferred; user wants to draw up a proper list next session rather than fix piecemeal now.
- **Related, smaller bug in the same area, root-caused this session but not fixed:** `population_tables.py`'s `extract_submissions` reads `organisationCode`/`organisationName` from the Indicators API response — these two field names were never actually confirmed against a real payload, unlike `organisationId`, `submissionId`, `anonSubmissionCode`, `dateId`, `result` (all also read in `transformers.py`, confirmed working there). Likely wrong key names, hence blank/fallback org name+code on newly-added `nhs_organisations` rows. Worth noting: the NHS toolkit's own `get_organisations` uses `nhsCode`, not `organisationCode`, for its code field — a hint the Indicators API's actual key may differ too. Bundled into the same future "list" as the id-mismatch problem, since a lookup-table fix would likely replace this code path anyway.
- Possible lead noted for that future session: `project_id` looks like a genuinely shared concept across both toolkit front-ends (same domain, same URL numbering scheme), even though `organisation_id` may not be — worth deciding how much of the identity problem is systemic vs isolated to organisations before scoping the fix.
- TimeSeries period cutting (single period / range) still not built — every chart currently renders every period. Explicitly out of scope for now, by user instruction ("we'll start by charting everything, and then decide how to cut this in practice").
- Tweaks (reference lines, axis control, conditional colouring) — unchanged, still not built; applies to TimeSeries the same as every other shape.
- One-hop-only `soft_parents` resolution, and the Charts tab's `set_default_populations` stopgap — both unchanged, carried forward as before.
- `format_modifier` retrofit — unchanged from last session's correction: CategoricalCompositional-only gap, not a three-shape one.

### Resolved / dropped this session

- **The maturity-statement gap** — resolved (Primer edit above). No longer an open question.
- **Installer release status** — user explicitly said not to raise this for now ("we're still in early days... no-one other than me is touching anything"). Dropped from active tracking; not to be raised again unless the user brings it up.
