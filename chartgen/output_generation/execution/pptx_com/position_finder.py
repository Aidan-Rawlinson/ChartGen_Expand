"""
position_finder.py
Position Finder -- a Running Order support tool, not a Running Order
function itself (not in assembly_engine.FUNCTION_MAP, never appears as a
row). Reads the currently-selected shape's live position/size straight off
an already-open PowerPoint instance, for copying into a Running Order row
by hand -- read-only, writes nothing back.

Standalone COM tool: attaches to the running PowerPoint instance via
GetActiveObject (never CreateObject, which would launch a fresh, empty
instance rather than find the one the user is actually looking at).

CG_Chart_{row_id} / CG_Link_{row_id} shape naming (assembly_engine.py,
insert_chart) is what makes the "is this a link icon, and if so which
chart is it attached to" question answerable at all -- see that module's
own naming comment for the row_id-renumbers-on-edit caveat, which applies
equally here: a name only stays accurate until the Running Order it came
from is next reordered/edited.
"""

EMU_PER_POINT = 12700  # PowerPoint COM reports shape geometry in points, not EMU


def _emu(points) -> int:
    return round(points * EMU_PER_POINT)


def get_selected_shape_position() -> dict:
    """
    Returns a dict describing the outcome. Always has a "status" key:
    "ok" or "error". On "ok", always has "kind" -- one of:

    - "chart_or_other": a plain shape (chart picture, or anything else the
      user happened to select) -- left_emu/top_emu/width_emu/height_emu
      are its own absolute position/size.
    - "link_with_chart": a CG_Link_ icon whose matching CG_Chart_ shape was
      found on the same slide -- hyperlink_left_emu/hyperlink_top_emu are
      offsets from that chart's own top-right corner (the same convention
      insert_chart's own hyperlink_left/hyperlink_top fields use), plus
      hyperlink_size_emu (the icon's own width, which insert_chart always
      draws square) and matched_chart_name for confirmation. Also still
      carries the icon's own absolute left_emu/top_emu/width_emu/height_emu,
      in case the offset isn't what's wanted.
    - "link_without_chart": a CG_Link_ icon whose matching CG_Chart_ shape
      isn't on the same slide (renamed, deleted, moved, or the name simply
      doesn't match any more) -- falls back to the icon's own absolute
      position/size, same fields as "chart_or_other", plus a "note"
      explaining the fallback.

    On "error", "message" explains why (PowerPoint not open/reachable, or
    nothing selected).
    """
    try:
        import pythoncom
        import comtypes.client
        # Explicit CoInitialize/CoUninitialize on this call, not relying on
        # comtypes' own implicit init -- same reasoning as save_pdf
        # (assembly_engine.py): comtypes' "have I initialised COM?" state
        # is a module-level flag, not per-thread, and Streamlit runs each
        # script rerun on a fresh thread.
        pythoncom.CoInitialize()
        try:
            try:
                powerpoint = comtypes.client.GetActiveObject("PowerPoint.Application")
            except OSError:
                return {"status": "error",
                        "message": "PowerPoint doesn't appear to be open. Open the "
                                   "generated .pptx in PowerPoint, select a shape, "
                                   "then try again."}

            try:
                selection = powerpoint.ActiveWindow.Selection
            except Exception:
                return {"status": "error",
                        "message": "Couldn't read the current selection -- is a "
                                   "presentation open and a slide showing?"}

            # ppSelectionShapes = 2 -- anything else (no selection, a slide
            # thumbnail, a text-editing caret inside a shape) isn't a shape
            # to report a position for.
            if selection.Type != 2 or selection.ShapeRange.Count == 0:
                return {"status": "error",
                        "message": "Nothing selected. Click a chart or link icon "
                                   "on the slide, then press this button again."}

            shape = selection.ShapeRange(1)  # COM collections are 1-indexed
            name = str(shape.Name or "")
            left_emu = _emu(shape.Left)
            top_emu = _emu(shape.Top)
            width_emu = _emu(shape.Width)
            height_emu = _emu(shape.Height)

            if name.startswith("CG_Link_"):
                row_id_suffix = name[len("CG_Link_"):]
                chart_name = f"CG_Chart_{row_id_suffix}"
                slide = shape.Parent
                matched_chart = None
                for i in range(1, slide.Shapes.Count + 1):
                    candidate = slide.Shapes(i)
                    if str(candidate.Name or "") == chart_name:
                        matched_chart = candidate
                        break

                if matched_chart is not None:
                    chart_left_emu = _emu(matched_chart.Left)
                    chart_top_emu = _emu(matched_chart.Top)
                    chart_width_emu = _emu(matched_chart.Width)
                    return {
                        "status": "ok",
                        "kind": "link_with_chart",
                        "name": name,
                        "matched_chart_name": chart_name,
                        "hyperlink_left_emu": left_emu - chart_left_emu - chart_width_emu,
                        "hyperlink_top_emu": top_emu - chart_top_emu,
                        "hyperlink_size_emu": width_emu,
                        "left_emu": left_emu, "top_emu": top_emu,
                        "width_emu": width_emu, "height_emu": height_emu,
                    }

                return {
                    "status": "ok",
                    "kind": "link_without_chart",
                    "name": name,
                    "note": f"No shape named '{chart_name}' found on this slide -- "
                            f"showing this icon's own absolute position instead.",
                    "left_emu": left_emu, "top_emu": top_emu,
                    "width_emu": width_emu, "height_emu": height_emu,
                }

            return {
                "status": "ok",
                "kind": "chart_or_other",
                "name": name,
                "left_emu": left_emu, "top_emu": top_emu,
                "width_emu": width_emu, "height_emu": height_emu,
            }
        finally:
            pythoncom.CoUninitialize()
    except ImportError:
        return {"status": "error",
                "message": "comtypes not available -- this tool requires "
                           "Windows + PowerPoint."}
    except Exception as e:
        return {"status": "error", "message": f"Position Finder failed: {e}"}
