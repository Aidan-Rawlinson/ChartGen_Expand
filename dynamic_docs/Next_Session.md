<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

The organisation-identity mismatch between the two toolkits is the live thread, and the user now has a **CSV extract for a map** ready to bring into next session — treat this as the trigger to finally move from "believed real" to actually verified and fixed. Covers at least:

1. **Use the CSV extract to confirm (or rule out) whether Indicators `organisation_id` genuinely doesn't match `nhs_organisations`' `unit_id` space.** This was the open verification step last session; the user now has the data to settle it.
2. **Design a lookup-table mechanism**, applied at the earliest point in the pipeline — before the `soft_parents` link between a submission and an organisation is made, not as a patch afterward. Likely means rethinking part of `toolkit_indicators/population_tables.py`'s merge logic, not just adding a translation step. Ask the user how they want the CSV brought into the tool (manual upload flow? static config file? something else) before designing the mechanism — don't assume.
3. **The `organisationCode`/`organisationName` field-name bug** in `extract_submissions` (unverified guessed keys) is probably subsumed by whatever the lookup-table fix ends up being, rather than needing its own separate patch.
4. **The project_id-shared-but-organisation_id-not asymmetry** — worth deciding explicitly how much of the identity problem is systemic (different backend, `icsapi` vs `membersapi`) vs isolated to organisations specifically.

Secondary, lower-priority items once the above is scoped:

- The three TimeSeries charts (built two sessions ago) and the new Charts sheet round-trip (built this session) both still haven't had a real batch-run test pass against a live workfile/template. Worth suggesting if the user has a natural gap, but don't push it over the org-identity work unless they want to switch.
- TimeSeries period cutting (single period/range) and Tweaks generally remain not built — pick back up once the org-identity work is settled, or sooner if the user wants to return to charting instead.

## Correction carried forward (still relevant, unchanged)

`format_modifier` retrofit: NumericSeries and NumericCompositional already populate it correctly from the API; only CategoricalCompositional lacks it. One-shape fix, not three, if this comes up again.

## Noted, not yet actioned

- **Placeholder removal alongside yellow-box removal** (raised this session, logged only, not built): the Template Reader strips yellow textboxes at Cleaned Template production but leaves the empty placeholder itself in place — visible in the PowerPoint editing view even though it doesn't render at output. No priority attached; raise if the user brings it up, or opportunistically if touching `template_reader.py` for the org-identity work.

## Open questions for the user

None outstanding from this session.

## Carried forward, not urgent

- One-hop-only `soft_parents` resolution is a deliberate scope boundary, not a bug — revisit only once a genuine multi-level chain (more than two tables deep) is actually needed.
- `format_modifier` — CategoricalCompositional-only gap (see above).
