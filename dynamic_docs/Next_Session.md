<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

Two items requested by the user for next session, not yet scoped:

1. **An easy update on the population tables.** No detail given yet — ask the user what specifically they have in mind before starting.
2. **A transformation that creates a metric data shape from a line-chart data shape.** Likely relates to converting a TimeSeries (or a chart's line-chart rendering) into one of the metric-based canonical shapes (NumericSeries/NumericCompositional/CategoricalCompositional) — but this is a guess, not confirmed. Ask the user to describe the intended source and target shapes and the use case before designing anything; don't assume which "line chart" or which "metric" they mean.

## Secondary, lower priority

- The `organisationCode`/`organisationName` field-name bug in `extract_submissions` (unverified guessed keys) is now a narrower concern than before — it only feeds the enrichment fallback path for an organisation not present in the current year's NHS organisations list (see Current_State), rather than the primary identity path. Worth verifying against a live `reportDataDatesSpecificOptions` response if it ever surfaces in practice (e.g. the fallback path actually gets hit), but not urgent — the fallback is a rare edge case (a resolved organisation retired from the NHS list).
- **Real data-quality gap surfaced this session:** some submissions in the underlying ics database have no matching organisation at all — caught correctly by the new unmapped-organisation warning during a clean test run. This is a database issue, not a ChartGen bug. The user said they'd investigate separately; no action needed from this side unless asked.
- The three TimeSeries charts and the Charts sheet round-trip (both built in earlier sessions) still haven't had a real batch-run test pass against a live workfile/template. Worth suggesting if the user has a natural gap.
- TimeSeries period cutting (single period/range) and Tweaks generally remain not built.

## Correction carried forward (still relevant, unchanged)

`format_modifier` retrofit: NumericSeries and NumericCompositional already populate it correctly from the API; only CategoricalCompositional lacks it. One-shape fix, not three, if this comes up again.

## Noted, not yet actioned

- **Placeholder removal alongside yellow-box removal**: the Template Reader strips yellow textboxes at Cleaned Template production but leaves the empty placeholder itself in place — visible in the PowerPoint editing view even though it doesn't render at output. No priority attached; raise if the user brings it up.

## Open questions for the user

- What exactly is meant by "an easy update on the population tables"?
- What are the source and target shapes for "the transformation that creates a metric data shape from a line chart data shape" — and what's the use case driving it?

## Carried forward, not urgent

- One-hop-only `soft_parents` resolution is a deliberate scope boundary, not a bug — revisit only once a genuine multi-level chain (more than two tables deep) is actually needed.
- `format_modifier` — CategoricalCompositional-only gap (see above).
