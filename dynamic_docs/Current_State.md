<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE -- READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the six governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base -- which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously -- during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in -- expect churn, don't resist it.
>
> **Standing rule (confirmed by the user, still in force): Base Charts and Base Tables are never documented in the governed docs -- not their existence, not their internals.** Only a genuine core-system-level change belongs there. Do not log a new Base Chart/Table's existence "for completeness."

## Status: Mapped all 26 NHS-database chart types (from a user-supplied list of stored procedures) to ChartGen's canonical data shapes. 25 of 26 resolved to the existing four shapes (some with caveats). The 26th (Sunderland/Modified Barthel chart) needed a genuinely new fifth canonical shape, PairedSurveyData -- designed and built this session. Per-unit `metadata` on the shared `Unit` base class (needed for cross-service charts) is still design-only, not yet coded.

### This session's work

**Full stored-procedure-to-data-shape mapping completed.** User supplied a table of 26 NHS-database chart types (Standard, Survey, Cross-service groups) each tied to a stored procedure name. Cross-referenced against `toolkit_nhs/transformers.py`'s `PROCEDURE_MAP` and `toolkit_indicators/transformers.py` to establish which were already supported in code before asking the user to resolve the rest. Final mapping (paste-into-Excel form given to user, reproduced here for reference):

```
Chart name	SP name	Data shape
Standard Benchmarking barchart	sp_a_generic_bar_chart_parameter_controls	NumericSeries
Difference Benchmarking barchart	sp_a_generic_difference_bar_chart	NumericSeries
Clustered Benchmarking barchart	sp_a_generic_multiple_dual_bar_alt_sort_order	NumericSeries
100% Stacked Benchmarking barchart	sp_a_generic_stacked_bar_chart	NumericSeries
Stacked Benchmarking barchart	sp_a_generic_dual_bar_chart	NumericSeries
General Summary barchart	sp_a_generic_dual_bar_chart_national_avg_vs_submission	NumericSeries (multiple Metric-Series)
Vacancy Rate Summary barchart	sp_a_generic_dual_bar_chart_vacancy_rate	NumericSeries (multiple Metric-Series)
Scatter plot	sp_a_generic_scatter_graph_chart	NumericSeries
Opening Hours	sp_a_generic_time_start_finish_chart	NumericSeries
Cross-service Standard Benchmarking barchart	sp_a_generic_bar_chart_cross_service	NumericSeries + per-unit metadata
Cross-service Difference Benchmarking barchart	sp_a_generic_difference_bar_chart_cross_service	NumericSeries + per-unit metadata
Radar compositional chart	sp_a_generic_radar_chart	NumericCompositional (has_valid_unit_data caveat)
Clustered compositional barchart	sp_a_generic_radar_to_dual_bar	NumericCompositional (has_valid_unit_data caveat)
Clustered compositional barchart + benchmark	sp_a_generic_stacked_bar_chart_primary_secondary_metric	NumericCompositional (second Metric-Series carries a local benchmark)
Cross-service Clustered compositional barchart	sp_a_generic_dual_bar_chart_percentage_split_cross_service	NumericCompositional + per-unit metadata
Survey - Clustered compositional barchart (numeric)	sp_a_generic_survey_age_dual_bar_chart2	NumericCompositional
Survey - Clustered compositional barchart (List)	sp_a_generic_list_dual_bar_chart_nhsi_ld	NumericCompositional (list values become counts)
Survey - Clustered compositional barchart (Yes/No)	sp_a_generic_survey_yn_dual_bar_chart	NumericCompositional (Yes/No values become counts)
Referral to start chart	sp_a_generic_survey_dual_bar_chart4	NumericCompositional
List piechart	sp_a_generic_list_pie_chart	CategoricalCompositional
Yes No chart (standard)	sp_a_generic_yn_chart_exclude_na	CategoricalCompositional
Yes No chart including "NA"	sp_a_generic_yn_chart	CategoricalCompositional
List based stacked barchart	sp_a_generic_list_stacked_bar_chart	CategoricalCompositional (multiple Metric-Series)
Median timeseries	sp_a_generic_series_timeseries_all_org_median_chart	TimeSeries
Percentage change timeseries	sp_a_generic_timeseries_percentage_change_chart	TimeSeries
Sunderland/Modified Barthel chart	sp_a_generic_survey_sunderland_score_chart	PairedSurveyData (new shape, designed this session, not yet built)
```

Note: NumericSeries's existing multi-Metric-Series support (`values: list[float]` per unit, one entry per named metric) already covers what looked at first glance like it might need a new shape -- it doesn't. Cross-service charts also needed no new shape, only a new per-unit metadata capability (below).

**Per-unit `metadata: dict` added to the shared `Unit` base class (design only, not yet coded), all four existing shapes.** Cross-service charts (3 of the 26) draw their population from more than one service at once; which service a given unit belongs to varies per fetch, so it can't be a peer-group column on a static population table (`population_layers.py`'s peer-group resolution is keyed to one standing population table per token). It has to travel on the per-unit record itself, same as `unit_code`/`unit_id` already do. Follows the existing shape-level `metadata` pattern exactly (Decision 37) but per-unit: open-ended dict, no predefined key schema required to be valid -- `service_id`/`service_name` are the first intended use, not a fixed contract.

**New canonical data shape designed: PairedSurveyData**, for the Sunderland/Modified Barthel chart. Per unit, a list of individual patient records (`patient_label` -- a plain distinguishing string like "Patient 1", no further meaning; `start_value`; `end_value`), rather than one value or one set of proportional components. Always exactly one Metric-Series (confirmed by user, not designed to extend), so it follows the flat NumericSeries structural pattern (a single `units` list) rather than the `metrics`-list pattern NumericCompositional/CategoricalCompositional use. Stats are pooled across every record across every surviving unit after any population filter (not averaged from pre-computed per-unit stats) -- same recompute-after-filter discipline every existing shape's `filter_*` function already follows. Stats block, to start: `count_with_data` (record has at least one of start/end present), `count_null` (neither present), `mean_start`, `mean_end` -- deliberately minimal, no median/quartiles/min/max yet. No PII concern -- confirmed `patient_label` is a positional index, not an identifiable or pseudonymised patient reference.

**Built this session.** New module `core/shared/normalisation_containers/shapes/paired_survey_data.py`: `PairedObservation` (`patient_label`, `start_value`, `end_value`), `PairedSurveyDataUnit(Unit)` (a `records` list), `PairedSurveyDataStats` (`count_with_data`, `count_null`, `mean_start`, `mean_end`), `PairedSurveyData` (the shape itself, flat `units` list, same descriptive/metadata/has_valid_unit_data fields as every other shape), `compute_paired_survey_data_stats`, `paired_survey_data_summary_stats`, `filter_paired_survey_data`. Wired into `dispatch.py`'s three generic dispatch points (`filter_shape`, `summary_stats`, `shape_units`) and into `unit_has_data` (checks `records` for a present start/end value, alongside the existing `values`/`response` checks). Registered in `shapes/__init__.py`'s exports. Added `_from_dict_paired_survey_data` and a `DESERIALISE_MAP` entry in `cache_reader.py` for cache read support -- cache *write* needed no new code, since `cache_writer.py` serialises generically via `dataclasses.asdict`.

**Not yet done for PairedSurveyData:** no `REFERENCE_ROW_CONVERTERS` entry in `reference_ids.py`, so it doesn't yet participate in Summary Stat Tags. No transformer exists yet to actually populate it from `sp_a_generic_survey_sunderland_score_chart`'s API response -- the shape can be built, filtered, and have its stats read, but nothing fetches real data into one yet. No Base Chart renders it. Per-unit `metadata` on the shared `Unit` base class (the separate cross-service design from earlier this session) is also still not coded.

**A real problem surfaced and banked, not fixed:** `has_valid_unit_data` (set on every shape, `False` only for the radar family) is currently inert -- carried through caching and filtering unchanged, but nothing anywhere reads it to change behaviour. `population_layers.py` will filter the radar transformer's synthetic single "SAMPLE_AVG" unit as if it were real per-unit data, with nothing to stop or flag it. Reframed by the user as the real underlying issue: **Base Charts need to properly support charts that only ever show one unit's values at a time** (radar's actual behaviour, not a data-completeness bug). Banked as a task for a future session, not designed further this session.

### Known gaps / not yet done (carried forward, none touched this session)

- **`has_valid_unit_data` is inert and the underlying "single-unit-only chart" support gap is unaddressed** -- new this session, described above, needs its own design session.
- **PairedSurveyData is built but has no transformer, no Base Chart, and no Stat Tags integration yet** -- new this session, described above.
- **Per-unit `metadata` on the shared `Unit` base class is designed but not coded** -- needed before cross-service transformers can be built.
- The same `cell.value`-without-`number_format` gap may exist in Stat Tags', Chart Store's, and the Running Order's own Excel readers -- only the Output Table content path has been fixed; the others are an un-investigated, live risk of the same failure mode.
- Base Table trim (from an earlier session) is still a potential breaking change for any existing workfile using one of the eight removed styles -- not confirmed clear with the user.
- SVG transparent backgrounds for tables -- still deferred, case-by-case, per the user's own earlier plan.
- A residual "pixel or two too low" vertical offset in `table_cardtile`'s chart-cell placement -- still parked, not investigated.
- Any Running Order `.xlsx` already generated under the old (pre-fix) two-`tweaks`-column schema still needs regenerating -- carried forward from an earlier session, not touched this session.
