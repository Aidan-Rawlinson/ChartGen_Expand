"""
bundle.py
Builds the Custom Charts download bundle — a single, self-contained text
document combining the shared chart_inputs contract (contract.py), the
current chart's own source code, and its live data for the chart actually
on screen. Designed to be dropped whole into a fresh chat with no other
context: everything needed to reason about and modify the chart is in
this one document.
"""

import dataclasses
import inspect
import json

from chartgen.output_generation.execution.charts.base_charts import CHART_REGISTRY
from chartgen.output_generation.execution.charts.custom_charts.contract import build_static_sections


def _get_chart_source(base_chart_name: str, custom_chart_code: dict) -> str:
    """
    Built-in: read the whole module the function lives in, not just the
    function itself — each Base Chart module carries its own inlined
    helpers/constants (Decisions.md; every chart is a standalone artefact,
    no shared internal helpers module), so inspect.getsource on the
    function object alone would silently drop everything it depends on.
    Custom: stored source text is already the complete file as pasted in.
    """
    if base_chart_name in CHART_REGISTRY:
        module = inspect.getmodule(CHART_REGISTRY[base_chart_name])
        return inspect.getsource(module)
    if custom_chart_code and base_chart_name in custom_chart_code:
        return custom_chart_code[base_chart_name]
    raise ValueError(f"Unknown base_chart_name: {base_chart_name}")


def _layers_to_json(population_layers: list) -> str:
    """Serialise the live population_layers passed to this chart, as-is, to JSON text."""
    return json.dumps([dataclasses.asdict(layer) for layer in population_layers], indent=2, default=str)


def build_bundle(base_chart_name: str, shape_type: str, population_layers: list,
                 width_emu: int, height_emu: int, tweaks: str, custom_chart_code: dict = None) -> str:
    """
    Build the complete Custom Charts download document for one chart, as
    currently configured and rendering on screen.
    """
    source = _get_chart_source(base_chart_name, custom_chart_code)
    live_data = _layers_to_json(population_layers)

    return f"""\
{build_static_sections()}

## This chart's data shape

The `population_layers` below are the **{shape_type}** shape. See the
fields present in the live data section further down for its exact
structure — every field that exists on this shape appears there.

## Current code for this chart ("{base_chart_name}")

This is the complete file, exactly as it will run — every import,
constant, and helper function, together with the entry-point function
itself. There is nothing outside what's shown below.

```python
{source}
```

## Live data for this chart, right now

This is the actual `population_layers` this chart is currently being
called with — the same data you would need to reason about to check any
change you make.

width_emu = {width_emu}
height_emu = {height_emu}
tweaks = "{tweaks}"

```json
{live_data}
```
"""
