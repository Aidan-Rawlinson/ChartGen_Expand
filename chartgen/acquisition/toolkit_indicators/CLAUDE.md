# toolkit_indicators

Mirrors `toolkit_nhs/` in shape. Different API host, different URL shape, different population-table model. Do not assume a rule from the NHS side applies here.

## Population tables

`merge_timeseries_population` merges on **every** fetch, not only the first. One response returns a project's entire period history, so even the first build has to union submissions across every period in that one call, and submissions genuinely drop in and out of the population over time.

Same append-by-`unit_id`, no-overwrite rule as `nhs_organisations`, just run every time.

Submissions tables are named `submissions_timeseries_{project_id}`. No year component: this toolkit has periods, not years.

## Organisation identity

The two databases' organisation id spaces do not match. `soft_parents` links a submission to `nhs_organisations:{unit_id}` through a live mapping from the project submissions response, resolved fresh on every fetch, per project.

An organisation absent from that mapping is still added, with no `soft_parents` link and a blank `Region()`. One warning per fetch run, not per submission.

## Periods

Each report has its own independent period numbering. The same calendar month can be a different `period_id` in two different reports. There is no shared, cross-report period-id space.

`availableDates` is kept in full, in the API's own order, unfiltered. Filtering it by anything time-dependent bakes fetch timing into cached data.
