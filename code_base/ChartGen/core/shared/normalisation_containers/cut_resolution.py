"""
cut_resolution.py
Composes the shared middle of the normalisation-at-the-boundary pipeline
for one chart's own "cut" of an already-loaded data shape: period-range
trim -> metric-periods conversion -> population-table/target-rows/
selected-ids resolution. The final step, build_population_layers, is left
to each caller to call directly against its own populations string — it's
already a shared, single-purpose function, and one caller (the Charts
sheet) needs target_rows for its own populations widget (peer-group
options) before it knows which populations string it wants to resolve,
so bundling that final call in here would force an ordering that doesn't
fit every caller.

Three callers each need exactly this pipeline against an already-loaded
shape plus a textual cut specification (a populations string, and
TimeSeries-only period fields) — insert_chart (assembly_engine.py) against
a Running Order row's own fields, the Charts sheet (charts_tab.py) against
its sandbox's own fields, and stat tags (stat_tags.py) against a
text_stats.csv row's own fields. What differs between them is only how the
cut specification and the loaded shape are obtained in the first place,
and how a failure should be surfaced (an err_result; a Streamlit warning;
a silently skipped tag) — this module owns only the shared middle,
deliberately raising rather than swallowing exceptions, so each caller
keeps its own existing error-handling policy around the call.

Lives in shared/normalisation_containers, not output_generation, because
none of it touches pptx, Streamlit, or the cache — it is pure data-shape
normalisation, the same tier as population_layers.py and
shape_transforms.py, one level up from both (this composes them). Loading
a shape from the cache stays with each caller — that step differs enough
per caller (cache_file vs hex_id, different "not found" handling) that
folding it in here would trade three clear call sites for one blurry one.
"""

from core.shared.infrastructure.period_ids import parse_metric_periods_string
from core.shared.normalisation_containers.shapes import apply_period_range
from core.shared.normalisation_containers.shape_transforms import maybe_convert_periods_to_metrics


def prepare_chart_cut(
    data_shape, shape_type: str,
    start_period: str, end_period: str, metric_periods_str: str,
    tables: dict, table_order: list, full_unit_set: dict,
):
    """
    Apply one chart's own period-range trim and metric-periods conversion
    to an already-loaded data shape, then resolve which population table
    its units belong to and which ids within it are "Selected" for the
    current reporting unit — everything build_population_layers needs
    except the populations string itself, which the caller supplies
    separately (see module docstring for why).

    start_period/end_period trim the shape's period axis first (TimeSeries
    only, no-op otherwise); metric_periods_str then converts the (possibly
    trimmed) shape into a NumericSeries snapshot if set, again TimeSeries
    only — applied in this order so a metric_periods id already trimmed
    out by the range correctly surfaces as "not found" rather than
    silently succeeding against the untrimmed shape.

    The population table a chart's units belong to is read off the shape
    itself (data_shape.population_table), not assumed to be the workfile's
    current master table — falling back to table_order[0] only for legacy
    cached data fetched before population_table existed.

    Returns (cut_shape, effective_shape_type, target_rows, selected_ids):
      - cut_shape is data_shape after the period-range trim and
        metric-periods conversion (identical to the input if neither
        applied) — a caller building its own "no populations resolved"
        fallback (e.g. insert_chart's "All" fallback) should use this, not
        the original data_shape, so the fallback reflects those same trims.
      - effective_shape_type is "NumericSeries" rather than the shape's own
        "TimeSeries" once a metric_periods conversion has actually been
        applied — the same distinction the Charts sheet and insert_chart
        both track (Decision 12) — otherwise shape_type unchanged.
      - target_rows / selected_ids are exactly build_population_layers'
        own `units`/`selected_ids` parameters, ready to pass straight
        through.

    Raises ValueError if metric_periods names a period_id not present on
    the (period-range-trimmed) shape — the same exception
    maybe_convert_periods_to_metrics itself raises; not caught here so each
    caller keeps its own existing policy for surfacing it.
    """
    if start_period or end_period:
        data_shape = apply_period_range(data_shape, start_period, end_period)

    effective_shape_type = shape_type
    metric_period_ids = parse_metric_periods_string(metric_periods_str or "")
    if metric_period_ids:
        data_shape = maybe_convert_periods_to_metrics(data_shape, metric_period_ids)
        effective_shape_type = "NumericSeries"

    target_table = data_shape.population_table or (table_order[0] if table_order else "")
    target_rows = tables.get(target_table, [])
    selected_ids = {r["unit_id"] for r in full_unit_set.get(target_table, [])}

    return data_shape, effective_shape_type, target_rows, selected_ids
