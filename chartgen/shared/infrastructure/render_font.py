"""
render_font.py
The font family every chart and table render draws in, applied around the
render call rather than inside the renderer. Owned here so the ChartGen
side of the mechanism has a single definition rather than a copy per call
site, exactly as render_scale.py owns the scale factor.

The family itself is not defined here. It is a stored user choice, read
from the open workfile's settings, so changing font is a setting rather
than a code edit.

Unlike CHART_RENDER_SCALE, this one does reach the Base Charts and Base
Tables, because matplotlib's rcParams is a single process-wide object and
those files read it at draw time. That is why they no longer set
font.family themselves: an assignment at module level in one of those
files belongs to whichever file imported last, not to the file that wrote
it, so it never reliably did what it appeared to. Full reasoning in
output_generation/execution/charts/base_charts/CLAUDE.md.

## Why the availability check is explicit

Matplotlib's own response to a font family it cannot find is to substitute
DejaVu Sans and write a line through the logging module. Three things make
that useless as a failure signal here:

  - it is a log record, not a warning and not an exception, so nothing in
    ChartGen sees it and it lands in the console behind Streamlit
  - the lookup is cached, so it appears once per process at most and never
    again for that family
  - every Base Chart and Base Table calls warnings.filterwarnings("ignore")
    at import, which front-loads a permanent catch-all filter for the whole
    process, so routing anything through the warnings machinery is futile

A substituted font is also worse than it first looks. Text is kept as real
<text> in the SVG, so the family *name* is what reaches PowerPoint, which
resolves it against locally installed fonts and substitutes again, on its
own terms. The two substitutions need not agree, so a chart can be laid out
against the metrics of one font and displayed in another.

Checking the family ourselves and refusing is therefore the only route to
the standing fail-visibly rule.
"""

import matplotlib
from matplotlib import font_manager


def font_is_available(family: str) -> bool:
    """
    Whether matplotlib holds a face under this family name, and would
    therefore draw in it rather than substituting.

    Asks matplotlib rather than the bundled fonts folder on purpose. The
    Settings tab offers only bundled families, but a name that arrived any
    other way is still a fair question, and a font genuinely installed on
    the machine is genuinely renderable.
    """
    if not family:
        return False
    return family in font_manager.fontManager.get_font_names()


def render_font(family: str):
    """
    Context manager setting the font family for one render, and refusing
    rather than substituting if that family is not available.

        with render_font(family):
            image_bytes = chart_func(population_layers, ...)

    Scoped to the block, so it applies to that render and leaves the rest
    of the process alone.

    Raises ValueError on an empty family - an open workfile with no default
    font set - and on a family matplotlib cannot resolve. Both messages name
    the Settings tab, because both are fixed there.
    """
    if not family:
        raise ValueError(
            "No default font is set for this workfile, so there is nothing to "
            "render text in. Set one on the Settings tab."
        )

    if not font_is_available(family):
        raise ValueError(
            f"The default font for this workfile (\"{family}\") is not "
            "available on this machine, so text would be drawn in a "
            "substitute font without matching what PowerPoint displays. "
            "Pick an available font on the Settings tab, which lists the "
            "fonts ChartGen ships and installs."
        )

    return matplotlib.rc_context({"font.family": family})
