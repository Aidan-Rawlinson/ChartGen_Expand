<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

Step 1 of the expansion plan (manifest table) is done and live-tested. The natural next piece is **Step 2 — multi-project, same database**: adding a URL for a new project_id+year combination triggers a submissions fetch, a new submissions table, and expansion of the organisations table. Same project_id but different year counts as a different project.

Design questions to settle before/while building Step 2 (from this session's planning discussion):

1. **Submissions vs organisations relationship.** The organisations table expands to hold organisations from multiple projects; submissions tables are per-project records of participation. The user explicitly wants to discuss this relationship before building — start here.
2. **Master table concept.** With multiple population tables, something must tell the system which table drives the batch loop and the reporting-unit picker. Load-bearing for everything downstream; table relationships come later, not in Step 2.
3. **units.csv model.** Currently one flat `units.csv` with `UNITS_FIELDNAMES` owned by workfile_file. Multi-table needs a structural decision (multiple CSVs? a table-of-tables?) — a .cgw structure change, so another file version bump.
4. **Parked from Step 1:** whether `data_updated_at`-style facts should ever live in two places was resolved by consolidation this time; keep the single-source instinct as tables multiply.

## Open questions for the user

- Step 2 kickoff: how should the "new project detected" moment surface in the UI — silent on fetch, or a visible confirmation step?
- Credential persistence (parked from planning): session-only, or per-machine like the stored username (Architecture Decision 7)? Needed by Step 4 at the latest.
- The maturity-statement gap (docs read more finished than the tool is) was flagged but never resolved — the Primer is the natural home and is edit-locked, so it needs an explicit decision. Decision on hold with the user.

## Carried forward from the installer session (not urgent)

- Test the real "update available" path (bump local software_id, run Check for Update, revert).
- Decide the real first release version — note software id is now 0.0.2 locally but the SharePoint release copy is still the 0.0.1 build; any release needs the Installer_Guide checklist run.
- Consider Uninstall Delete scope on a second pass.
- Installer_Guide.md sits outside the six-document ground-truth discipline — occasional manual check.
