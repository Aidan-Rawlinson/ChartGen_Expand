<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

Multi-project/same-database work (submissions/organisations tables, `soft_parents`, master table, automatic per-chart trigger) is done and live-tested. The natural next piece is **Second database** — new timeseries data shape, new Base Charts, a credential requirement per database, organisation ID collision handling.

Design questions worth settling before/while building it, given how population tables now actually work:

1. **Does a second database change anything about `population_table` naming?** Today's convention (`table_naming.py`) is nhs-specific (`submissions_{year}_{project_id}`). A second database will need its own naming convention — does it get its own `table_naming`-style module, or does the naming function need a database parameter?
2. **Credential requirement.** Does a second database need its own credentials box on the Imports tab? How does URL-to-database triage decide which credential set applies to a given URL *before* fetch — is that decided by parsing the URL alone, or does it need a lookup?
3. **Organisation ID collision handling.** `nhs_organisations`' merge-by-`unit_id` logic currently assumes one shared id space across every project on the workfile. If a second database's organisation ids can collide with or duplicate nhs organisation ids (same raw id, different real-world entity), that assumption breaks — needs a decision on how identity is disambiguated across databases before the merge logic can be trusted with two databases in play.

## Open questions for the user

- **Credential persistence** (parked across several sessions now): session-only, or per-machine like the stored username (Architecture Decision 7)? Needed once a second database exists and Imports needs to hold more than one credential set.
- **The maturity-statement gap** (docs read more finished than the tool is) — still unresolved. Primer is the natural home and is edit-locked, so it needs an explicit decision from the user before Claude touches it.
- **Installer release** — `0.0.3` was walked through (Inno Setup compile → test → copy to SharePoint) but completion wasn't confirmed before this Close-down. Worth checking at the start of next session whether it actually shipped.

## Carried forward, not urgent

- One-hop-only `soft_parents` resolution is a deliberate scope boundary, not a bug — revisit only once a genuine multi-level chain (more than two tables deep) is actually needed.
- Charts tab's `set_default_populations` read is an acknowledged stopgap (reads one Running Order row's value directly) — fine to leave until it causes a real problem.
