<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Status: The Indicators/NHS organisation-identity mismatch is resolved and confirmed working against live data. `Region()` and organisation names now flow correctly into both `nhs_organisations` and the Indicators submissions table. Governed docs updated to match.

### What works (built this session)

- **Organisation identity resolution, Indicators ↔ NHS.** Confirmed live: the two databases' organisation id spaces genuinely do not match (the earlier same-id assumption in `population_tables.py` was wrong).
  - **First pass (retired):** built a stopgap static CSV lookup (`org_lookup.py` + `static_config/ics_org_lookup.csv`, a one-off DB extract of ics `organisation_id` → `external_organisation_id`), wired into `merge_timeseries_population`.
  - **Superseded same session:** discovered that `/projects/{id}/submissions` — the same endpoint already called for visible dates — also returns `userOrganisations`, giving the identical `organisationId → externalOrganisationId` mapping live, per project, plus each submission's real `submissionName`. On the user's explicit instruction, the CSV approach was fully retired in favour of this live data: `org_lookup.py` and `static_config/ics_org_lookup.csv` deleted, along with the resulting stale `.pyc`; confirmed no dangling references anywhere in the codebase.
  - `api_client.get_visible_dates` renamed to `get_project_submissions_data`, now returns the full response (`projectDates` + `userOrganisations`) rather than discarding everything but the dates.
  - `fetch.py` builds `org_id_map` and `submission_name_map` from that response once per project per fetch run, and passes both into `merge_timeseries_population`.
  - **Region()/name enrichment:** when a resolved organisation isn't yet in `nhs_organisations`, it's now enriched via `toolkit_nhs.api_client.get_organisations` (queried against the current calendar year — confirmed with the user as the intended stand-in, since Indicators data has no year of its own) for its canonical name and `Region()`, rather than being built from the Indicators response's own (incomplete) values. Falls back to the Indicators-side name/blank `Region()` only if the organisation genuinely isn't in that year's NHS list.
  - Submission `Region()` is resolved from this same now-enriched data within the same merge pass, so a submission whose organisation is newly discovered in this fetch still gets the correct `Region()` immediately, not one fetch later.
  - **Unmapped organisations:** a submission whose `organisation_id` has no live mapping entry is still added, with no `soft_parents` link and `Region()` left blank — no invented value, minimum footprint. `fetch.py` accumulates one `any_unmapped_org` flag across the whole run and appends a single synthetic `"warning"`-status result rather than one per submission; `imports_tab.py`'s flash-message loop now renders `"warning"` status distinctly from `"ok"`/`"error"`.
  - **Submission naming bug fixed:** `unit_name` was previously set to the same anonymised code as `unit_code` (no real name was ever being extracted). Now sourced from the live `submission_name_map`'s real `submissionName`; `unit_code` remains `anonSubmissionCode` — the two fields are genuinely different now.
- **Confirmed working end-to-end** via a clean test run (fresh workfile, first-time table creation): organisations and peer groups now flow correctly. The test also surfaced a real data-quality issue — some submissions in the underlying database have no matching organisation at all — which the new unmapped-organisation warning correctly caught. That's a database gap, not a ChartGen bug; parked for the user to investigate separately.
- **Governed docs updated to match** (Primer untouched, per its edit lock): Functional Spec §7.4 (the project-level call's description, and the organisation-link/enrichment/naming paragraph), Architecture (module table row for `toolkit_indicators/`, and Decision 10's "Organisation identity assumption" rewritten as "Organisation identity resolution").

### Known gaps / not yet done

- **Next session: an easy update on the population tables**, and **the transformation that creates a metric data shape from a line chart data shape** — both requested by the user for next time, not yet scoped in detail. See Next_Session.
- The `organisationCode`/`organisationName` field-name bug in `extract_submissions` (unverified guessed keys, sourced from `report_data`'s own `organisationList`, not `userOrganisations`) is narrower now than before — it's only ever used as the enrichment fallback for an organisation not present in the current year's NHS organisations list — but the keys themselves remain unverified against a live response.
- TimeSeries period cutting (single period/range) — not built.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) — not built.
- One-hop-only `soft_parents` resolution — deliberate scope boundary, not a bug.
- `format_modifier` retrofit — CategoricalCompositional-only gap, unchanged.
- The three TimeSeries charts and the Charts sheet round-trip (both built in earlier sessions) still haven't had a real batch-run test pass into a live template — unchanged from last session.

### Resolved / dropped this session

- **Organisation-identity mismatch between the two toolkits** — resolved. Confirmed real, root-caused, fixed, and tested against live data.
- **Static CSV lookup stopgap** — built, then retired the same session in favour of the live per-project mapping discovered partway through (see above). No trace left in the codebase.
- **Submission `unit_name` == `unit_code` bug** — resolved. Real submission names now flow through.

### Noted, not yet actioned

- **Placeholder removal alongside yellow-box removal.** Cleaned-template production strips yellow textboxes but leaves the placeholder itself in place; an empty placeholder is still visible in the PowerPoint editing view (though it doesn't render at output). Carried forward, unchanged — no priority attached.
