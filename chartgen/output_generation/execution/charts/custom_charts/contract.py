"""
contract.py
Single source of truth for the Custom Charts feature: the chart_inputs
contract, the allowed-imports whitelist, and the banned-names list. Used by
both gate.py (the static check that enforces these rules) and bundle.py
(the download bundle that explains them to whoever is editing the chart) —
so the list a person is told they can use and the list actually enforced
can never drift apart.

A custom Base Chart is treated the same way an Excel .crtx chart-type
template is treated: a rendering artefact, not application logic. It must
be fully standalone — no import from ChartGen's own code — for the same
reason every built-in Base Chart now is (see
chartgen/output_generation/execution/charts/base_charts/__init__.py):
whatever isn't visible in the downloaded bundle can't be edited by whoever
receives it.
"""

# Root module names a custom chart may import. Checked against the first
# dotted component only, so "matplotlib.pyplot", "matplotlib.patches",
# "matplotlib.ticker", "matplotlib.colors" etc. are all covered by
# "matplotlib" appearing here once. Extend this list, not the gate's logic,
# if a future chart genuinely needs another library — this is the one
# place that decision lives.
ALLOWED_IMPORTS = ["matplotlib", "numpy", "io", "warnings", "math"]

# Bare builtin names a custom chart may never call. Import restriction
# above already keeps os/sys/subprocess etc. unreachable via attribute
# access (they can't be imported in the first place), so this list only
# needs to cover builtins that are always in scope without any import.
BANNED_NAMES = ["open", "exec", "eval", "__import__", "compile", "globals", "locals", "vars"]

CHART_INPUTS_EXPLANATION = """\
## What this document is

This is a ChartGen Base Chart — a rendering function that draws one chart
from data. Treat it the same way you'd treat an Excel custom chart-type
template (.crtx): it only ever produces a picture. It has no access to,
and must never gain access to, anything else in the surrounding
application — no file system, no network, no other part of the system
that generated this data.

This document is everything you will be given. There is no further
technical information available beyond what's written here, and no way to
ask a clarifying question about the system this came from — treat this as
a complete, standalone handoff.

## Who you're helping

The person you're working with is not a programmer. They will describe
what they currently see, and what they'd like different, in plain,
non-technical language — for example "make the highlighted bar a
different colour" or "I don't want a title on this" or "can the numbers
show fewer decimal places" — not in terms of matplotlib calls, variable
names, or any of the concepts below. Translate their description into the
corresponding code change yourself. Don't ask them for technical specifics
they won't have; make a reasonable interpretation and produce a complete,
working function.

## The chart_inputs contract

Every Base Chart function receives exactly four parameters, in this
order, and returns exactly one thing:

    def my_chart(population_layers: list, width_emu=5486400, height_emu=3429000, tweaks=""):
        ...
        return image_bytes

- **population_layers** — an ordered list. Each entry is one filtered copy
  of the chart's data, carrying a `population_label` field (e.g. "All",
  "Selected", or the name of a peer group). The first entry in the list is
  always the overall scope — the full population this chart compares
  against. Every entry after that is a highlight layer within that scope:
  "Selected" is the individual unit(s) currently being reported on; any
  other label is a resolved peer group. A layer can genuinely contain zero
  units (nothing currently resolves to that label) — this is expected
  behaviour, not an error, and every chart type in this system already
  handles it by simply drawing nothing extra for that layer.
- **width_emu**, **height_emu** — integers, the size in EMU (English
  Metric Units — 914400 per inch), the same unit PowerPoint itself stores
  every shape's size in. Not a percentage, not pixels — a real physical
  size. To convert to inches for a `matplotlib` figure's own `figsize`,
  divide by 914400.

  Important: these are **already scaled up** from the size the chart will
  actually be displayed at — every Base Chart is called at a fixed
  multiple of its real, final on-screen size (currently 5x), then placed
  back on the slide/page at that real size afterward, which shrinks the
  whole rendered image back down uniformly. This is a workaround for a
  PowerPoint bug that otherwise mis-spaces individual characters in text
  kept as real `<text>` (see the font instructions below for why that
  matters here). You don't need to account for this in width_emu/
  height_emu themselves — just use them exactly as given, the same as
  before — but you **do** need to scale every absolute point-based size
  in your own code (font sizes, line widths, marker sizes) by that same
  multiple, or your chart's own text and lines will come out looking
  proportionally far too small once displayed at real size. See the font
  instructions below for exactly how.
- **tweaks** — a free-text string, blank by default. Nothing in the wider
  system currently parses this string's contents — if you want to make
  some part of the chart's appearance configurable, you're free to invent
  your own small syntax inside this string and read it yourself.

## Allowed imports

Only these libraries may be imported: {allowed_imports}. Nothing else is
available in the environment this function will run in — no other part of
the codebase, no file system access, no network access, no other
third-party package. Plan the implementation around this constraint.

## Return contract

The function must return image bytes — the same thing every existing
Base Chart returns: a `matplotlib` figure saved to an in-memory buffer via
`fig.savefig(buf, format="svg", ...)` (SVG, not PNG — every Base Chart is
rendered as a vector image, not a raster one), with the buffer returned
(not the figure object itself, and not a Matplotlib Axes/Figure).

Font must be Calibri, and text must be kept as real text rather than
converted to glyph outlines — set both once, near the top of the file,
right after the matplotlib imports:

    import matplotlib
    matplotlib.rcParams["font.family"] = "Calibri"
    matplotlib.rcParams["svg.fonttype"] = "none"

Then define a local scale constant, and multiply every absolute
point-based size in the file by it — font sizes, line widths, marker
sizes, dash-pattern lengths, anything specified in points rather than as
a fraction of the axes/figure:

    TEXT_SCALE = 5

    ax.plot(x, y, linewidth=1.5 * TEXT_SCALE)
    ax.set_xticklabels(labels, fontsize=7 * TEXT_SCALE)
    ax.scatter(x, y, s=40 * (TEXT_SCALE ** 2))   # scatter's own "s" is an area, not a length -- square the scale factor

This number (5) must match exactly — it isn't something to tune per
chart. If a value is already computed as a fraction of the axes/figure
(anything in the 0-1 data-coordinate or figure-fraction space, rather
than points or inches) it already scales correctly on its own and needs
no multiplication.

## Submitting your answer

The code shown to you below is the complete file, top to bottom —
imports, constants, every helper function, and the entry-point function
together. Return your answer the same way: the complete file, in full,
as a single Python code block, ready to be pasted back in and run exactly
as you return it. Do not return only the function you changed, only a
diff, or only the new/edited parts — anything you leave out is lost, since
nothing outside this one file exists for it to fall back on.

Your reply should contain that one Python code block and nothing else.
Do not repeat, summarise, or include the live data shown further below —
it was given to you only so you can reason about whether your change
works against real values; it is not part of what you send back, and the
person receiving your reply has no use for it repeated to them.

You're free to add, remove, or rename helper functions as needed — every
existing Base Chart already has several (palette constants, sizing,
formatting helpers), and there's no limit on how many you use. The one
rule: exactly one function in the file must be the entry point, accepting
the four chart_inputs parameters shown above (population_layers, width_emu,
height_emu, tweaks) — that's the one the system will call. Any other functions
are treated as private helpers and aren't restricted beyond the
allowed-imports rule above, which applies to the whole file.
"""


def build_static_sections() -> str:
    """
    Render the shared, chart-agnostic sections of the bundle (framing,
    interaction model, chart_inputs contract, allowed imports, return
    contract, submission format). Identical for every chart — the only
    parts that vary per chart (data shape schema, current code, live data)
    are supplied by bundle.py and slotted around this.
    """
    return CHART_INPUTS_EXPLANATION.format(allowed_imports=", ".join(ALLOWED_IMPORTS))
