"""
paired_survey_data.py
PairedSurveyData — per unit, a collection of individual patient records each
carrying a start/end value pair (e.g. Sunderland/Modified Barthel scores) —
with its stats recalculation and population-filtering.

Always exactly one Metric-Series, and not intended to extend, so this uses a
flat shape-level units list with no metrics wrapper.

Stats are pooled across every record across every unit, not averaged from
per-unit stats, and are recomputed from the raw records after any
population filter.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from chartgen.shared.normalisation_containers.shapes.common import Unit, ShapeStats


@dataclass
class PairedObservation:
    """One patient's before/after record within a unit."""
    patient_label: str             = ""    # e.g. "Patient 1" — a plain distinguishing label, no further meaning
    start_value:   Optional[float] = None
    end_value:     Optional[float] = None


@dataclass
class PairedSurveyDataUnit(Unit):
    """One unit's set of patient records."""
    records: list[PairedObservation] = field(default_factory=list)


@dataclass
class PairedSurveyDataStats:
    """Stats pooled across every record across every unit. Deliberately minimal to start."""
    count_with_data: Optional[int]   = None  # records with at least one of start/end present
    count_null:      Optional[int]   = None  # records with neither present
    mean_start:      Optional[float] = None
    mean_end:        Optional[float] = None


@dataclass
class PairedSurveyData:
    """Per-unit collections of individual patient start/end score records."""
    # Descriptive fields
    title:              Optional[str]       = None
    year:               Optional[int]       = None
    format_modifier:    Optional[str]       = None
    population_label:   Optional[str]       = None  # resolved population-string token label, set by build_population_layers
    population_table:   Optional[str]       = None  # name of the population table this data's units belong to

    # Travels with the shape without being part of it. Not in the
    # chart_inputs contract. Carries through filtering and replace().
    metadata:           dict                = field(default_factory=lambda: {"source_url": None})

    # Data
    has_valid_unit_data: bool               = True
    units:              list[PairedSurveyDataUnit] = field(default_factory=list)

    # Stats — shape level, then the single pooled stats block (always exactly one Metric-Series)
    shape_stats:        ShapeStats           = field(default_factory=ShapeStats)
    stats:              PairedSurveyDataStats = field(default_factory=PairedSurveyDataStats)


def compute_paired_survey_data_stats(units: list) -> "PairedSurveyDataStats":
    """
    Compute PairedSurveyDataStats pooled across every record across every
    given unit. The single canonical implementation — used both when the
    shape is first built from API data and when it is recalculated after
    population filtering.
    """
    all_records = [r for u in units for r in u.records]
    count_with_data = sum(1 for r in all_records if r.start_value is not None or r.end_value is not None)
    count_null = len(all_records) - count_with_data

    start_values = [r.start_value for r in all_records if r.start_value is not None]
    end_values = [r.end_value for r in all_records if r.end_value is not None]

    return PairedSurveyDataStats(
        count_with_data=count_with_data,
        count_null=count_null,
        mean_start=round(sum(start_values) / len(start_values), 4) if start_values else None,
        mean_end=round(sum(end_values) / len(end_values), 4) if end_values else None,
    )


def paired_survey_data_summary_stats(shape: "PairedSurveyData") -> dict:
    """
    Summary statistics for a PairedSurveyData shape — everything on tap,
    independent of any visualisation. Always exactly one Metric-Series, so
    keyed by the shape's own title (falling back to a fixed label) rather
    than iterating a metrics list, to keep the same {name: {...}} shape
    the other three summary_stats functions return.
    """
    name = shape.title or "Paired Survey Data"
    return {
        name: {
            "n":              shape.stats.count_with_data,
            "No data":        shape.stats.count_null,
            "Mean Start":     shape.stats.mean_start,
            "Mean End":       shape.stats.mean_end,
        }
    }


def filter_paired_survey_data(shape: "PairedSurveyData", unit_ids: set) -> "PairedSurveyData":
    """Return a new PairedSurveyData filtered to unit_ids with stats recalculated."""
    filtered_units = [u for u in shape.units if u.unit_id in unit_ids]
    new_stats = compute_paired_survey_data_stats(filtered_units)
    new_shape_stats = ShapeStats(
        count_metric_series=1,
        count_units=len(filtered_units),
        count_units_with_any_data=sum(1 for u in filtered_units if any(
            r.start_value is not None or r.end_value is not None for r in u.records
        )),
    )
    return replace(shape, units=filtered_units, stats=new_stats, shape_stats=new_shape_stats)
