<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

The organisation-identity mismatch between the two toolkits is the live thread. User wants to draw up a proper list next session, covering at least:

1. **Confirm whether Indicators `organisation_id` genuinely doesn't match `nhs_organisations`' `unit_id` space.** User is fairly confident it doesn't, but this hasn't been verified against real data yet.
2. **Design a lookup-table mechanism**, applied at the earliest point in the pipeline — before the `soft_parents` link between a submission and an organisation is made, not as a patch afterward. This will likely mean rethinking part of `toolkit_indicators/population_tables.py`'s merge logic, not just adding a translation step.
3. **The `organisationCode`/`organisationName` field-name bug** in `extract_submissions` (unverified guessed keys — see Current_State) is probably subsumed by whatever the lookup-table fix ends up being, rather than needing its own separate patch.
4. **The project_id-shared-but-organisation_id-not asymmetry** — worth deciding explicitly how much of the identity problem is systemic (different backend, `icsapi` vs `membersapi`) vs isolated to organisations specifically.

Secondary, lower-priority items once the above is scoped:

- The three new TimeSeries charts have only been discussed/reasoned through this session, not confirmed against a live batch run into a real template — worth a real test pass.
- TimeSeries period cutting (single period / range) and Tweaks generally remain not built — pick back up once the org-identity work is settled, or sooner if the user wants to return to charting instead.

## Correction carried forward (still relevant, unchanged)

`format_modifier` retrofit: NumericSeries and NumericCompositional already populate it correctly from the API; only CategoricalCompositional lacks it. One-shape fix, not three, if this comes up again.

## Open questions for the user

None outstanding. The maturity-statement gap is resolved (Primer edited this session). The installer release question has been explicitly dropped per the user's instruction — do not raise it again unless they do.

## Carried forward, not urgent

- One-hop-only `soft_parents` resolution is a deliberate scope boundary, not a bug — revisit only once a genuine multi-level chain (more than two tables deep) is actually needed.
- Charts tab's `set_default_populations` read is an acknowledged stopgap (reads one Running Order row's value directly) — fine to leave until it causes a real problem.
- `format_modifier` — CategoricalCompositional-only gap (see above).
