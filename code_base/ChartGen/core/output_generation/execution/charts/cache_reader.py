"""
cache_reader.py
Loads a canonical data shape from WorkfileState's cache by filename.
"""

import json

from core.shared.normalisation_containers.shapes import (
    NumericSeries, NumericSeriesUnit, NumericSeriesMetricStats, ShapeStats,
    NumericCompositional, NumericCompositionalMetric, NumericCompositionalUnit,
    NumericCompositionalMetricStats,
    CategoricalCompositional, CategoricalCompositionalMetric,
    CategoricalCompositionalUnit, CategoricalCompositionalMetricStats,
)


def _from_dict_numeric_series(d):
    units = [
        NumericSeriesUnit(
            unit_code=u["unit_code"],
            unit_id=u["unit_id"],
            values=u["values"],
        )
        for u in d.get("units", [])
    ]
    metric_stats = [
        NumericSeriesMetricStats(**ms)
        for ms in d.get("metric_stats", [])
    ]
    return NumericSeries(
        title=d.get("title"),
        metric_names=d.get("metric_names", []),
        year=d.get("year"),
        format_modifier=d.get("format_modifier"),
        has_valid_unit_data=d.get("has_valid_unit_data", True),
        units=units,
        shape_stats=ShapeStats(**d.get("shape_stats", {})),
        metric_stats=metric_stats,
    )


def _from_dict_numeric_compositional(d):
    metrics = []
    for m in d.get("metrics", []):
        units = [
            NumericCompositionalUnit(
                unit_code=u["unit_code"],
                unit_id=u["unit_id"],
                values=u["values"],
            )
            for u in m.get("units", [])
        ]
        metrics.append(NumericCompositionalMetric(
            name=m.get("name"),
            component_names=m.get("component_names", []),
            units=units,
            stats=NumericCompositionalMetricStats(**m.get("stats", {})),
        ))
    return NumericCompositional(
        title=d.get("title"),
        year=d.get("year"),
        format_modifier=d.get("format_modifier"),
        has_valid_unit_data=d.get("has_valid_unit_data", True),
        metrics=metrics,
        shape_stats=ShapeStats(**d.get("shape_stats", {})),
    )


def _from_dict_categorical_compositional(d):
    metrics = []
    for m in d.get("metrics", []):
        units = [
            CategoricalCompositionalUnit(
                unit_code=u["unit_code"],
                unit_id=u["unit_id"],
                response=u.get("response"),
            )
            for u in m.get("units", [])
        ]
        metrics.append(CategoricalCompositionalMetric(
            name=m.get("name"),
            category_names=m.get("category_names", []),
            units=units,
            stats=CategoricalCompositionalMetricStats(**m.get("stats", {})),
        ))
    return CategoricalCompositional(
        title=d.get("title"),
        year=d.get("year"),
        has_valid_unit_data=d.get("has_valid_unit_data", True),
        metrics=metrics,
        shape_stats=ShapeStats(**d.get("shape_stats", {})),
    )


DESERIALISE_MAP = {
    "NumericSeries":            _from_dict_numeric_series,
    "NumericCompositional":     _from_dict_numeric_compositional,
    "CategoricalCompositional": _from_dict_categorical_compositional,
}


def _deserialise(json_str: str):
    wrapper = json.loads(json_str)
    shape_type = wrapper["shape_type"]
    data = wrapper["data"]
    if shape_type not in DESERIALISE_MAP:
        raise ValueError(f"Unknown shape_type in cache: {shape_type}")
    return DESERIALISE_MAP[shape_type](data), shape_type


def load_shape(filename, workfile_state):
    """Load a cached data shape by filename from WorkfileState.cache, returning (shape_instance, shape_type_string)."""
    return _deserialise(workfile_state.cache[filename])


def list_cached_files(workfile_state):
    """Return sorted list of cache filenames (excluding manifest), from WorkfileState.cache."""
    return sorted(workfile_state.cache.keys())


def load_manifest(workfile_state):
    """Return manifest dict keyed by filename, from WorkfileState.manifest."""
    return {v["filename"]: v for v in workfile_state.manifest.values()}
