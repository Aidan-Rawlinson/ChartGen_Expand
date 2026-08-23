# toolkit_nhs

## Population tables

`ensure_population_tables` builds a project's tables once, the first time that project and year is seen, then no-ops. It is called from `fetch.py` during a chart's own pull, before that chart's data is fetched. The first chart pulled for a project and year is what builds its tables.

`nhs_organisations` is shared across every project in a workfile. A further project appends organisations not already present, by `unit_id`. Existing rows are never touched and the table is never rebuilt.

This depends on `Region()` being handed over per organisation by the API. If it ever becomes something computed across the whole table, the append-only merge has to be revisited.

## Submission codes

The API pads the numeric part of `submissionCode` inconsistently: `"PH050"` and `"PH50 "` are the same code. `submission_codes.normalise_submission_code` trims, then re-pads to a minimum three-digit numeric part.

Apply it anywhere a raw `submissionCode` becomes a ChartGen `unit_code`. Currently every transformer reading it, plus `api_client.get_submissions`.
