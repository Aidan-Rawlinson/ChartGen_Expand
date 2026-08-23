"""
contract.py
Single source of truth for the Custom Tables feature: the table_inputs
contract, the allowed-imports whitelist, and the banned-names list. Used by
both gate.py (the static check that enforces these rules) and bundle.py
(the download bundle that explains them to whoever is editing the table)
-- so the list a person is told they can use and the list actually
enforced can never drift apart.

Mirrors chartgen.output_generation.execution.charts.custom_charts.contract
field-for-field, for the table domain rather than the chart domain. Kept
as its own copy, not shared with the charts version, since base_tables and
base_charts are deliberately separate rendering domains --
if tables ever need a different library allowance than charts, that's a
one-line change here with no risk to the chart side.

A custom Base Table is treated the same way a custom Base Chart is: a
rendering artefact, not application logic. It must be fully standalone --
no import from ChartGen's own code -- for the same reason every built-in
Base Table already is (base_tables/__init__.py): whatever isn't visible in
the downloaded bundle can't be edited by whoever receives it.
"""

# Root module names a custom table may import. Checked against the first
# dotted component only. Extend this list, not the gate's logic, if a
# future table genuinely needs another library.
ALLOWED_IMPORTS = ["matplotlib", "numpy", "io", "warnings", "math"]

# Bare builtin names a custom table may never call.
BANNED_NAMES = ["open", "exec", "eval", "__import__", "compile", "globals", "locals", "vars"]

TABLE_INPUTS_EXPLANATION = """\
## What this document is

This is a ChartGen Base Table -- a rendering function that draws one
table, as a single image, from a resolved grid of content. Treat it the
same way you'd treat an Excel custom chart-type template (.crtx): it only
ever produces a picture. It has no access to, and must never gain access
to, anything else in the surrounding application -- no file system, no
network, no other part of the system that generated this data.

This document is everything you will be given. There is no further
technical information available beyond what's written here, and no way to
ask a clarifying question about the system this came from -- treat this
as a complete, standalone handoff.

## Who you're helping

The person you're working with is not a programmer. They will describe
what they currently see, and what they'd like different, in plain,
non-technical language -- for example "make the borders thicker" or "I'd
like the header row shaded" or "can the text be a bit bigger" -- not in
terms of matplotlib calls, variable names, or any of the concepts below.
Translate their description into the corresponding code change yourself.
Don't ask them for technical specifics they won't have; make a reasonable
interpretation and produce a complete, working function.

## The table_inputs contract

Every Base Table function receives exactly six parameters, in this order,
and returns exactly two things:

    def my_table(content, column_widths, row_heights, width_emu=5486400, height_emu=3429000, tweaks=""):
        ...
        return image_bytes, chart_cells

- **content** -- a list of rows, each row a list of strings: the table's
  own content grid, already fully resolved -- every value the person
  authored is already plain text by the time it reaches you, with one
  exception: a cell can hold a chart-component marker, exactly the text
  "{{" followed by an id followed by "}}" (e.g. "{{C3}}") and nothing else.
  Recognise this pattern yourself (a plain string check is enough --
  starts with "{{", ends with "}}", and the text between them starts with
  "C" -- no need for a regex library). A cell holding one of these is not
  drawn as text at all -- see chart_cells below for what to do with it
  instead.
- **column_widths** -- a list of numbers, one per column, in the same
  column order as `content`. Each is that column's own width as a
  percentage of the table's total width. These numbers are expected to sum
  to approximately 100, but should not be assumed to sum to exactly 100.
- **row_heights** -- a list of numbers, one per row, in the same row order
  as `content`. Each is that row's own height as a percentage of the
  table's total height. Same approximate-100 expectation as column_widths.
- **width_emu**, **height_emu** -- integers, the size in EMU (English
  Metric Units -- 914400 per inch), the same unit PowerPoint itself
  stores every shape's size in. Not a percentage, not pixels -- a real
  physical size. To convert to inches for a `matplotlib` figure's own
  `figsize`, divide by 914400.

  Important: these are **already scaled up** from the size the table will
  actually be displayed at -- every Base Table is called at a fixed
  multiple of its real, final on-screen size (currently 5x), then placed
  back on the slide/page at that real size afterward, which shrinks the
  whole rendered image back down uniformly. This is a workaround for a
  PowerPoint bug that otherwise mis-spaces individual characters in text
  kept as real `<text>` (see the font instructions below for why that
  matters here). You don't need to account for this in width_emu/
  height_emu themselves -- just use them exactly as given, the same as
  before, and any chart_cells rectangle you report will already come out
  correctly in that same inflated space, matching what the wider system
  now expects -- but you **do** need to scale every absolute point-based
  size in your own code (font sizes, line widths, border widths) by that
  same multiple, or your table's own text and lines will come out
  looking proportionally far too small once displayed at real size. See
  the font instructions below for exactly how.
- **tweaks** -- a free-text string, blank by default. Nothing in the wider
  system currently parses this string's contents -- if you want to make
  some part of the table's appearance configurable, you're free to invent
  your own small syntax inside this string and read it yourself.

## Chart-component cells

A cell whose content is a chart marker ("{{C3}}", say) names a chart that
belongs in that cell -- but you never draw the chart itself. Your job for
that cell is: don't draw any text there, but do report back the exact
rectangle you would have drawn that cell's content in, in the same EMU
unit as width_emu/height_emu, measured from the table's own top-left
corner. Something else in the wider system draws the actual chart into
that rectangle afterwards.

Collect these into a dict as you go, one entry per chart-component cell
you find, keyed by the id inside the braces (without the braces
themselves -- "{{C3}}" becomes the key "C3"):

    chart_cells = {{
        "C3": {{"x": 1234000, "y": 456000, "width": 2000000, "height": 900000}},
    }}

If a table has no chart-component cells at all, return an empty dict --
`{{}}` -- for this second value; never omit it or return only the image
bytes on their own. No rotation or other transform is expected here, only
the cell's own position and size (resizing/placement only, nothing more
elaborate).

A cell's reported rectangle is a design decision, not a geometry lookup.
"The cell" is whatever visual area you're actually treating as usable
content space -- if your design adds padding, margin, a border, a drop
shadow, rounded corners, or any other deliberate inset around a chart
marker, the reported rectangle should reflect that narrower area, not the
raw column_widths/row_heights grid cell. If it isn't obvious which
reading the person wants, ask them, rather than assuming the raw grid
geometry is what they meant.

Technical trap, easy to get wrong invisibly: if your `matplotlib` figure
uses `bbox_inches="tight"` when saving -- needed whenever anything is
deliberately drawn outside the axes via `clip_on=False`, e.g. a bleeding
shadow or badge -- the saved canvas is NOT guaranteed to correspond 1:1
with the nominal (width_emu, height_emu) canvas you were asked to draw.
The crop can expand or shrink the saved image asymmetrically depending on
what actually bled outside the axes, and a chart-cell rectangle computed
as a naive fraction of the nominal canvas will silently drift out of
alignment. The fix is not to avoid `bbox_inches="tight"` (it's often
unavoidable for a design with overflowing decoration) -- it's to call
`fig.get_tightbbox(renderer)` after all drawing is complete and remap
every cell's data-space coordinates through the ACTUAL crop bounding box
(plus whatever `pad_inches` you save with) before converting to EMU,
rather than assuming your data axis maps linearly onto the declared
canvas. If your design draws nothing outside its own axes at all, the
simpler and preferred option is to drop `bbox_inches="tight"` entirely
and make your axes fill the whole figure explicitly
(`fig.add_axes([0, 0, 1, 1])`) instead of relying on `tight_layout` --
exact, with nothing to correct for afterwards.

## Allowed imports

Only these libraries may be imported: {allowed_imports}. Nothing else is
available in the environment this function will run in -- no other part
of the codebase, no file system access, no network access, no other
third-party package. Plan the implementation around this constraint.

## Return contract

The function must return a tuple of two things: image bytes, then the
chart_cells dict described above (an empty dict if there are none). The
image bytes are the same thing the built-in Base Table returns: a
`matplotlib` figure saved to an in-memory buffer via
`fig.savefig(buf, format="svg", ...)` (SVG, not PNG -- every Base Table is
rendered as a vector image, not a raster one), with the buffer itself
returned (not the figure object, and not a Matplotlib Axes/Figure).

Font must be Calibri, and text must be kept as real text rather than
converted to glyph outlines -- set both once, near the top of the file,
right after the matplotlib imports:

    import matplotlib
    matplotlib.rcParams["font.family"] = "Calibri"
    matplotlib.rcParams["svg.fonttype"] = "none"

Then define a local scale constant, and multiply every absolute
point-based size in the file by it -- font sizes, line widths, border
widths, anything specified in points or fixed inches rather than as a
fraction of the axes/figure:

    TEXT_SCALE = 5

    cell.set_linewidth(0.75 * TEXT_SCALE)
    ax.text(x, y, label, fontsize=8 * TEXT_SCALE)

This number (5) must match exactly -- it isn't something to tune per
table. If a value is already computed as a fraction of the axes/figure
(anything in the 0-1 data-coordinate or figure-fraction space, rather
than points or inches) it already scales correctly on its own and needs
no multiplication.

## Submitting your answer

The code shown to you below is the complete file, top to bottom --
imports, constants, every helper function, and the entry-point function
together. Return your answer the same way: the complete file, in full, as
a single Python code block, ready to be pasted back in and run exactly as
you return it. Do not return only the function you changed, only a diff,
or only the new/edited parts -- anything you leave out is lost, since
nothing outside this one file exists for it to fall back on.

Your reply should contain that one Python code block and nothing else. Do
not repeat, summarise, or include the live data shown further below -- it
was given to you only so you can reason about whether your change works
against real values; it is not part of what you send back, and the person
receiving your reply has no use for it repeated to them.

You're free to add, remove, or rename helper functions as needed. The one
rule: exactly one function in the file must be the entry point, accepting
the six table_inputs parameters shown above (content, column_widths,
row_heights, width_emu, height_emu, tweaks) -- that's the one the system will
call. Any other functions are treated as private helpers and aren't
restricted beyond the allowed-imports rule above, which applies to the
whole file.
"""


def build_static_sections() -> str:
    """
    Render the shared, table-agnostic sections of the bundle (framing,
    table_inputs contract, allowed imports, return contract, submission
    format). Identical for every table -- the only parts that vary per
    table (current code, live grid data) are supplied by bundle.py and
    slotted around this.
    """
    return TABLE_INPUTS_EXPLANATION.format(allowed_imports=", ".join(ALLOWED_IMPORTS))
