"""
text_engine.py
Running Order function: update_text — replaces text tags in the presentation
with values for the current reporting unit. Promoted out of assembly_engine
(where it was buried as a single function) to its own module, the same tier
as charts/pictures/excel under execution.

Two tag families, both resolved per report:
  - Per-unit tags (e.g. [selected-reporting-unit-name]) — one value per
    reporting unit, read straight off ReportContext.
  - Stat tags (workfile_config/text_stats.csv, stat_tags.py) — a short,
    permanent id (e.g. [T3], [Ta7]) standing in for one summary-stats value
    from one chart's own independently-authored cut of its cached data.

Covers ordinary text frames and, as of this session, PowerPoint table
cells too (shape.table) — previously the one remaining gap.
"""

from chartgen.output_generation.execution.results import ok_result, err_result
from chartgen.output_generation.execution.text.stat_tags import resolve_stat_tag_value
from chartgen.shared.infrastructure.value_formatting import format_reference_value

_RUN_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}r"
_T_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"


def build_stat_tag_tokens(workfile_state, full_unit_set: dict) -> dict:
    """
    Resolve every stat tag defined on this workfile to its current value for
    this report, keyed by its literal template text ("[<tag>]"). A tag that
    can't be resolved (deleted chart, layer/reference id no longer present)
    is simply omitted — its literal text is left untouched in the deck
    rather than replaced with something misleading.
    """
    tokens = {}
    for stat_row in getattr(workfile_state, "text_stats_rows", []):
        tag = str(stat_row.get("tag", "") or "").strip()
        if not tag:
            continue
        resolved = resolve_stat_tag_value(stat_row, workfile_state, full_unit_set)
        if resolved is None:
            continue
        tokens[f"[{tag}]"] = format_reference_value(
            resolved["value"], resolved["kind"], resolved["format_modifier"]
        )
    return tokens


def _replace_tags_in_text_frame(text_frame, tokens: dict) -> int:
    """
    Replace every tag in tokens across every paragraph of one text frame —
    the same interface an ordinary shape and a PowerPoint table cell both
    expose via python-pptx (.paragraphs / .runs), so this one routine
    covers both. Returns the number of individual tag replacements made.
    """
    replacements = 0

    for para in text_frame.paragraphs:
        runs = para.runs
        if not runs:
            continue

        full_text = "".join(r.text for r in runs)
        if not any(tok in full_text for tok in tokens):
            continue

        replaced = full_text
        for token, value in tokens.items():
            if token in replaced:
                replaced = replaced.replace(token, value)
                replacements += 1

        # Write the replaced text into the first run's <a:t> element, then
        # delete all subsequent runs from the paragraph XML.
        first_run_xml = runs[0]._r
        t_elem = first_run_xml.find(_T_TAG)
        if t_elem is not None:
            t_elem.text = replaced

        para_xml = para._p
        for run_elem in para_xml.findall(_RUN_TAG)[1:]:
            para_xml.remove(run_elem)

    return replacements


def update_text(ctx, row: dict, settings: dict) -> dict:
    """
    Replace text tags in the presentation with values for the current
    reporting unit — both the fixed per-unit tag and every defined stat
    tag (workfile_config/text_stats.csv). Covers ordinary text frames and
    table cells alike.
    """
    if ctx.prs is None:
        return err_result(row, "update_text: no open presentation (create_ppt not called?).")

    rc = ctx.report_context
    tokens = {}
    if rc:
        tokens["[selected-reporting-unit-name]"] = rc.unit_name or ""

    workfile_state = settings.get("workfile_state")
    if workfile_state is not None:
        tokens.update(build_stat_tag_tokens(workfile_state, ctx.full_unit_set or {}))

    if not tokens:
        return ok_result(row, "update_text: no tags to replace (no ReportContext, no stat tags).")

    replacements = 0
    for slide in ctx.prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                replacements += _replace_tags_in_text_frame(shape.text_frame, tokens)
            if shape.has_table:
                for table_row in shape.table.rows:
                    for cell in table_row.cells:
                        replacements += _replace_tags_in_text_frame(cell.text_frame, tokens)

    return ok_result(row, f"update_text: {replacements} replacement(s) made.")
