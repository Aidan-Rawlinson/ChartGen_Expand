"""
render_scale.py
The one factor by which every chart and table render call inflates its
target size before drawing, and by which the result is shrunk back when
placed. Owned here so the ChartGen side of the mechanism has a single
definition rather than a copy per call site.

This does NOT reach the Base Charts and Base Tables themselves. Those
files import nothing from ChartGen, by design, so each carries its own
TEXT_SCALE literal and the two values still have to be kept equal by
hand. Full mechanism, and the rules on what does and does not get
scaled, in output_generation/execution/charts/base_charts/CLAUDE.md.

Changing the value here therefore only does half the job. Every
TEXT_SCALE in base_charts/ and base_tables/ has to change with it.
"""

CHART_RENDER_SCALE = 5
