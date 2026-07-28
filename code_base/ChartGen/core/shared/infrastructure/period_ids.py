"""
period_ids.py
Tiny, generic '^'-delimited period-id list <-> string helpers — no
Running-Order-specific knowledge, just a format. Lives in shared so
data-shape-normalisation code (core.shared.normalisation_containers,
e.g. cut_resolution.py) can parse a metric_periods string without
depending on output_generation.definition (Architecture, Section 2 —
one-way dependencies: shared must not import from a higher layer).
core.output_generation.definition.running_order.dialog_support re-exports
both for its existing callers.
"""


def parse_metric_periods_string(metric_periods_str: str) -> list:
    """Parse a '^'-delimited metric_periods string into a list of period_ids."""
    if not metric_periods_str:
        return []
    return [p.strip() for p in metric_periods_str.split("^") if p.strip()]


def build_metric_periods_string(period_ids: list) -> str:
    """Build a '^'-delimited metric_periods string from a list of period_ids, in the order given."""
    return "^".join(period_ids)
