"""
common.py
Base structures shared across all three canonical data shapes.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Unit:
    """Identity fields shared by all per-unit entries across all shapes."""
    unit_code: str
    unit_id:   str


@dataclass
class ShapeStats:
    """Shape-level summary statistics, identical in structure across all three shapes."""
    count_metric_series:        Optional[int] = None  # number of Metric-Series in this shape
    count_units:                Optional[int] = None  # total units in population
    count_units_with_any_data:  Optional[int] = None  # units with data in at least one Metric-Series
