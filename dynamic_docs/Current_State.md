<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Status: This session added a `tweaks` column/parameter to the charting pipeline, then used the discussion around it to trigger a genuine architectural fix: Base Chart functions no longer compute or return statistics at all — image-only now — with statistics and unit lists read directly from the data shapes by whichever consumer actually needs them. All six governed documents were updated in the mirror to match.

### What works (built/fixed this session)

- **`tweaks` column and parameter, string-typed (Architecture Decision 16).** Every Base Chart function's `tweaks` parameter was typed `list` (`tweaks=[]`) but never read by any function body, and the Running Order had no matching column at all. Added a `tweaks` column to `schema.py`'s `COLUMNS`, retyped every Base Chart function's parameter to `tweaks=""` (all 20, across all four shape modules) and `registry.render_chart` to match. `assembly_engine.insert_chart` reads the row's `tweaks` column and passes it through; blank produces a nil-length string, never `None`. Added to `CHART_SANDBOX_FIELDS` and given its own text-area control in the Charts sheet, populating from a bound row's `tweaks` column the same way `populations`/`metric_periods` already do. No Base Chart function reads the value yet — the plumbing is complete, the behaviour isn't built.

- **Base Chart statistics ownership reversed to the data shapes (Architecture Decision 17).** Prompted by the user questioning why Base Chart functions — whose job is producing a visual — were computing and returning statistics at all. Investigation surfaced a real bug, not just a structural smell: the "Selected value" bolt-on was computed two different ways across NumericSeries chart functions of the same shape type (`ranked_column`/`dot_strip` read the scope layer directly; `box_whisker`/`frequency_histogram`/`violin_plot`/`bead_string_dot_plot` required an explicit "Selected" population layer) — the same unit/data could show a different "Selected value" purely by which chart type was picked. Also surfaced: the computed stats were never consumed anywhere — `AssemblyContext.summary_stats` was written once per chart and never read back by anything.
  - All 20 Base Chart functions now return `image_bytes` only. Every `summary_stats(base)` call and `_summary_stats_with_selection` wrapper removed from every return line; dead `sel_val`/`selected_value` tracking that existed solely to feed those returns removed too (not left as dead code).
  - `_summary_stats_with_selection` and `_selected_layer_value` (`base_charts/shared.py`) deleted outright — zero remaining callers.
  - `registry.render_chart` now just dispatches to the chart function and returns its image. Dropped its own `summary_stats_by_layer`/`units_by_layer` computation entirely.
  - `assembly_engine.py` — `AssemblyContext.summary_stats` attribute removed; `_render_chart_image` is now a thin pass-through returning bytes only.
  - `charts_tab.py` — preview call unpacks just `image_bytes`; `layer_summary_stats`/`layer_units` for the "Summary stats"/"Units included" display are now computed directly against `pop_layers` (already in scope) via `summary_stats_by_layer`/`units_by_layer`, not relayed through `render_chart`.

- **Documentation fully updated (mirror only, re-upload pending user confirmation).** All six static docs checked against the actual code and corrected:
  - **Architecture** — Running Order schema table and Decision 11's field list both gained `tweaks`; the `AssemblyContext` in-memory diagram lost `summary_stats: dict`; Decision 15 trimmed to remove now-false claims (4-tuple return, `AssemblyContext.summary_stats`, "render_chart's third and fourth return values") while keeping what's still true (the `summary_stats` rename, reference-ids construction, the always-present-population-layer fix, the zero-unit shape fixes); new Decision 16 (tweaks) and Decision 17 (statistics reversal) added.
  - **Functional Spec** — §9.3 field list gained `tweaks`; §10.3 rewritten from "not built" to describe the real column/parameter/round-trip; §10.5 Autotables corrected — no data collection happens today.
  - **Feature List** — Charts sheet round-trip row gained `tweaks`; Autotables row downgraded from Partial to Not built with corrected description.
  - **Glossary** — `AssemblyContext` entry lost "summary stats"; `CHART_SANDBOX_FIELDS` entry gained `tweaks`; `Autotable`/`Summary stats` entries corrected to "read on demand" rather than "collected at chart time"; `Tweak` entry notes the plumbing exists without behaviour.
  - Primer and Docs Maintenance Guide needed no changes.

### Known gaps / not yet done (carried forward)

None.

### Resolved / dropped this session

- `tweaks` parameter type — from an unused `list` default to a wired-through `string`, with a real Running Order column and Charts sheet control (Decision 16).
- Base Chart statistics/unit-list return — from a 4-tuple every chart function computed and returned (2 inconsistent methods for "Selected value," and a result nothing ever consumed) to image-only, with stats read on demand directly from the shapes (Decision 17).
- Documentation drift from the above two changes — fully corrected across all six documents in the mirror.
