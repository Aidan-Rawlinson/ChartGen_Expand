<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

- **Docs re-upload — pending.** The mirror is fully updated and ahead of Project Files; confirm with the user whether the re-upload happened at Close-down, and if not, do it first thing next session before trusting Project Files as current.
- User flagged more work is planned on the charting process next session, specifically continuing to simplify what ChartGen is trying to achieve in this area — no specific next feature named yet, so ask rather than assume a direction.

## This session's work, for context

- **`tweaks` column/parameter** — added a `tweaks` Running Order column and retyped every Base Chart function's `tweaks` parameter from an unused `list` default to a wired-through `string` (Architecture Decision 16). Added to `CHART_SANDBOX_FIELDS` with its own Charts sheet text-area control. No Base Chart function reads the value yet — plumbing only.
- **Base Chart statistics ownership reversed to the data shapes** (Architecture Decision 17) — the user's instinct that "base_charts exist to create visual outputs, statistics are the property of data_shapes" was correct and surfaced a real bug: two different NumericSeries chart functions computed "Selected value" two genuinely different ways, and the computed stats were never consumed by anything downstream (`AssemblyContext.summary_stats` written once, read never). All 20 Base Chart functions now return `image_bytes` only; `registry.render_chart` returns just the image; `assembly_engine.py` and `charts_tab.py` both read stats/units directly from `population_layers` on demand instead of via a relayed return value.
- **All six governed documents updated in the mirror** to match both changes above — see Current_State.md for the full per-document breakdown. Primer and Docs Maintenance Guide needed no changes.
- If Autotables is ever built, `data_shape`/`population_layers` are already in scope at the right point in `assembly_engine.insert_chart` to call `summary_stats_by_layer` directly — no new plumbing needed to wire it up.
