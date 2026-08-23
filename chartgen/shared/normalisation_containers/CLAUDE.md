# normalisation_containers

Data-shape normalisation. No pptx, no Streamlit, no cache access.

## Population layer resolution

`build_population_layers` produces one layer per token in the populations string. Always. An unresolvable token returns an empty id set carrying its own best-available label, never `None` and never a skipped layer.

The scope token is the first token. If it resolves empty, every later token resolves empty against it. The layer list does not collapse.

Resolution depends only on the population table. It never depends on whether the chart has data for the selected unit.

## Cut resolution

`prepare_chart_cut` is the shared middle used by `insert_chart`, the Charts sheet, Stat Tags, the Chart Store and Output Tables: period-range trim, then metric-periods conversion, then population-table, target-rows and selected-ids resolution.

It deliberately excludes loading the shape from cache. That step differs per caller and stays with the caller. Callers also call `build_population_layers` themselves.

Numeric extraction from `start_period`, `end_period` and `metric_periods` happens here and nowhere else in the system, via `shared/infrastructure/period_ids.py`. Every caller passes its stored value through unmodified.

An unresolvable `metric_periods` id is a no-data case, not an error. It becomes its own output metric with every value `None`, labelled with the bare id in parentheses.

## Cross-shape conversion

`shape_transforms.py` sits here rather than in `shapes/` because converting between two shapes needs to know about both, and neither shape module may depend on the other.
