"""
text_engine.py
Running Order function: update_text — replaces text tags in the presentation
with values for the current reporting unit. Promoted out of assembly_engine
(where it was buried as a single function) to its own module, the same tier
as charts/pictures/excel under execution.

Partial: table cells (shape.table) are not yet covered — see Feature List,
Text / variable content.
"""

from core.output_generation.execution.results import ok_result, err_result


def update_text(ctx, row: dict, settings: dict) -> dict:
    """
    Replace text tags in the presentation with values for the current reporting unit.
    Tags: [selected-reporting-unit-name] → unit_name.
    """
    if ctx.prs is None:
        return err_result(row, "update_text: no open presentation (create_ppt not called?).")

    rc = ctx.report_context
    tokens = {}
    if rc:
        tokens["[selected-reporting-unit-name]"] = rc.unit_name or ""

    if not tokens:
        return ok_result(row, "update_text: no tags to replace (no ReportContext).")

    # XML namespace for DrawingML text runs
    _run_tag = "{http://schemas.openxmlformats.org/drawingml/2006/main}r"
    _t_tag   = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"

    replacements = 0

    for slide in ctx.prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                runs = para.runs
                if not runs:
                    continue

                # Check whether the full paragraph text contains any tag
                full_text = "".join(r.text for r in runs)
                needs_replace = any(tok in full_text for tok in tokens)
                if not needs_replace:
                    continue

                # Apply all tag replacements to the full paragraph text
                replaced = full_text
                for token, value in tokens.items():
                    if token in replaced:
                        replaced = replaced.replace(token, value)
                        replacements += 1

                # Write the replaced text into the first run's <a:t> element,
                # then delete all subsequent runs from the paragraph XML.
                first_run_xml = runs[0]._r        # lxml element for the run
                t_elem = first_run_xml.find(_t_tag)
                if t_elem is not None:
                    t_elem.text = replaced

                # Remove every run element after the first from the paragraph XML
                para_xml = para._p
                run_elements = para_xml.findall(_run_tag)
                for run_elem in run_elements[1:]:
                    para_xml.remove(run_elem)

    return ok_result(row, f"update_text: {replacements} replacement(s) made.")
