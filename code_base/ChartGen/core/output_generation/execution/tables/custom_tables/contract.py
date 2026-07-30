"""
contract.py
Single source of truth for the Custom Tables feature: the table_inputs
contract, the allowed-imports whitelist, and the banned-names list. Used by
both gate.py (the static check that enforces these rules) and bundle.py
(the download bundle that explains them to whoever is editing the table)
-- so the list a person is told they can use and the list actually
enforced can never drift apart.

Mirrors core.output_generation.execution.charts.custom_charts.contract
field-for-field, for the table domain rather than the chart domain. Kept
as its own copy, not shared with the charts version, since base_tables and
base_charts are deliberately separate rendering domains (Decisions.md) --
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
and returns exactly one thing:

    def my_table(content, column_widths, row_heights, width=80, height=50, tweaks=""):
        ...
        return image_bytes

- **content** -- a list of rows, each row a list of strings: the table's
  own content grid, already fully resolved -- every value the person
  authored is already plain text by the time it reaches you. There is
  nothing left to look up or substitute.
- **column_widths** -- a list of numbers, one per column, in the same
  column order as `content`. Each is that column's own width as a
  percentage of the table's total width. These numbers are expected to sum
  to approximately 100, but should not be assumed to sum to exactly 100.
- **row_heights** -- a list of numbers, one per row, in the same row order
  as `content`. Each is that row's own height as a percentage of the
  table's total height. Same approximate-100 expectation as column_widths.
- **width**, **height** -- integers, the target size as a percentage of
  the shorter dimension of the output page (not pixels, not inches, not
  EMU).
- **tweaks** -- a free-text string, blank by default. Nothing in the wider
  system currently parses this string's contents -- if you want to make
  some part of the table's appearance configurable, you're free to invent
  your own small syntax inside this string and read it yourself.

## Allowed imports

Only these libraries may be imported: {allowed_imports}. Nothing else is
available in the environment this function will run in -- no other part
of the codebase, no file system access, no network access, no other
third-party package. Plan the implementation around this constraint.

## Return contract

The function must return image bytes -- the same thing the built-in Base
Table returns: a `matplotlib` figure saved to an in-memory buffer via
`fig.savefig(buf, format="png", ...)`, with the buffer returned (not the
figure object itself, and not a Matplotlib Axes/Figure).

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
row_heights, width, height, tweaks) -- that's the one the system will
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
