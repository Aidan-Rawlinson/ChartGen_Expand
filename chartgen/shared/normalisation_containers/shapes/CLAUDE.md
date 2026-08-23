# shapes

Five canonical data shapes, one module each: NumericSeries, NumericCompositional, CategoricalCompositional, TimeSeries, PairedSurveyData. Four have Base Charts. PairedSurveyData has none, has no `chart_type_map.csv` row, and has no `REFERENCE_ROW_CONVERTERS` entry, so it does not participate in Stat Tags.

Each module owns its own stats computation and summary statistics. Generic behaviour dispatches in `dispatch.py`, keyed on the shape-type strings also used by `chart_type_map.csv` and `cache_reader.DESERIALISE_MAP`.

Shared fields are duplicated per shape deliberately, not pulled into a base class. `common.py` holds only `Unit` and `ShapeStats`.

## Adding a shape-level field

Two places rebuild a shape field by field and will silently reset a new field to its default unless it is added explicitly:

- `output_generation/execution/charts/cache_reader.py`, the five `_from_dict_*` deserialisers
- `shared/normalisation_containers/shape_transforms.py`, the TimeSeries to NumericSeries conversion

Cache writing needs no change. `cache_writer.save_chart` serialises any shape generically.

## Zero-unit layers

Stats must derive counts from structural fields (`metric_names`, `component_names`, `category_names`, `periods`), never from unit data. A layer with no units still returns one stats entry per metric-series.

## Adding a shape

Wire it into `filter_shape`, `summary_stats` and `shape_units` in `dispatch.py`, into `unit_has_data`, into `shapes/__init__.py` exports, and into `cache_reader.DESERIALISE_MAP`.
