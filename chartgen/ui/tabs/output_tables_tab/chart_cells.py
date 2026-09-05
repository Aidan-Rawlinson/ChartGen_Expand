"""
chart_cells.py
The "{Cn}" chart-component cell: rendering one Chart Store entry at a
table cell's own rectangle, and splicing the results into the table's own
SVG for on-screen preview. Preview only -- the final report layers a
separate PowerPoint picture instead (insert_table.py), and never merges
two SVG documents.

Also holds this package's own _svg_preview_html.
"""

import base64

from chartgen.output_generation.execution.charts.chart_store import resolve_chart_store_population_layers
from chartgen.output_generation.execution.charts.custom_charts import get_chart_callable
from chartgen.shared.infrastructure.font_embed import font_face_css
from chartgen.shared.infrastructure.render_font import render_font


def _svg_preview_html(svg_text, width_css, family):
    """
    Forces an SVG's rendered size to width_css (a CSS width value, e.g.
    "480px" or "100%") via an inline style on the SVG's own root element,
    since st.markdown has no width parameter the way st.image does. Used
    instead of st.image because st.image goes through PIL, which can't
    decode SVG, and every Base Table returns SVG bytes.

    Carries family's own @font-face block alongside the SVG, so the
    browser's SVG text engine -- a different renderer from matplotlib, with
    its own font lookup -- can draw the SVG's <text> elements in the right
    font without needing it installed on the machine. See font_embed.py.

    Does not reach any {Cn} chart cell spliced into this same SVG -- each
    of those is a nested <image> data URI (see _splice_chart_cells_into_svg),
    an isolated document a page-level <style> block cannot see into, so
    each carries its own copy instead.
    """
    styled = svg_text.replace("<svg ", '<svg style="width:100%;height:auto;display:block" ', 1)
    return f'{font_face_css(family)}<div style="width:{width_css}">{styled}</div>'


def _render_chart_store_chart_preview(chart_store_row: dict, chart_rect: dict,
                                       workfile_state, full_unit_set: dict):
    """
    Preview-side equivalent of insert_table.py's own
    _render_chart_store_chart -- population_layers resolution itself is
    shared (chart_store.resolve_chart_store_population_layers), so this
    function only adds what's specific to actually rendering: the
    base_chart_name lookup and the render call at the cell's own rectangle.
    Returns None on any failure -- one broken chart cell doesn't block the
    rest of the preview.

    chart_rect is in the table's own render-space (CHART_RENDER_SCALE
    times real size -- see that constant's own comment), since the
    enclosing table_func call is. Used here exactly as given, with no
    further multiplication -- that's already the correctly-inflated size
    a Base Chart expects to be called with under this same mechanism.

    The workfile's default font is applied here in its own right. A chart
    cell renders after the enclosing table's own image is finished, outside
    that render's font scope, so it needs its own wrap or it would draw in
    whatever font happened to be in force.
    """
    base_chart_name = str(chart_store_row.get("base_chart_name", "") or "").strip()
    if not base_chart_name:
        return None

    population_layers = resolve_chart_store_population_layers(chart_store_row, workfile_state, full_unit_set)
    if not population_layers:
        return None

    tweaks = str(chart_store_row.get("tweaks", "") or "").strip()
    try:
        chart_func = get_chart_callable(base_chart_name, workfile_state.custom_chart_code)
        with render_font(workfile_state.settings.get("default_font", "")):
            return chart_func(
                population_layers,
                width_emu=int(round(chart_rect["width"])),
                height_emu=int(round(chart_rect["height"])),
                tweaks=tweaks,
            )
    except Exception:
        return None


def _embed_font_in_svg(svg_text: str, family: str) -> str:
    """
    Inserts family's own @font-face block as a child of svg_text's own
    <svg> root, right after the opening tag closes.

    A nested <image xlink:href="data:image/svg+xml;..."> is an isolated
    document -- the browser renders it the same way it would a separate
    .svg file, so a <style> block on the host page never reaches it. SVG
    natively supports a <style> child, and that travels with the document
    wherever it's loaded, so giving the chart's own SVG this before it is
    embedded is what lets it resolve its own <text> elements' font-family.
    """
    insert_at = svg_text.index(">", svg_text.index("<svg ")) + 1
    return svg_text[:insert_at] + font_face_css(family) + svg_text[insert_at:]


def _splice_chart_cells_into_svg(table_svg_text: str, chart_cells: dict, workfile_state,
                                  full_unit_set: dict, width_emu: int, height_emu: int) -> str:
    """
    Preview-only compositing: embeds each chart cell's own rendered chart
    as a nested <image> data URI inside the table's own SVG, positioned as
    a percentage of the table's own declared width/height (recovered from
    each cell's EMU rectangle) rather than absolute pixels -- percentages
    resolve against whatever the table's own SVG viewport actually ends up
    being (post any bbox_inches="tight" crop, post the CSS stretch
    _svg_preview_html applies), so this stays visually aligned with the
    cell borders the same Base Table function drew, which used the exact
    same percent coordinates internally, rather than needing to reverse-
    engineer matplotlib's own crop margins from outside it.

    Only for on-screen preview -- the final report instead layers a
    separate PowerPoint picture (insert_table.py), never merges SVG
    documents: an <image> reference is fully opaque to the
    browser, so there's no risk of the two SVGs' own internal ids/styles
    colliding the way directly inlining one SVG's markup into another's
    would be.
    """
    if not chart_cells or not width_emu or not height_emu:
        return table_svg_text

    default_font = workfile_state.settings.get("default_font", "")
    chart_store_by_id = {r.get("chart_store_id"): r for r in workfile_state.chart_store_rows}
    inserts = []
    for tag, rect in chart_cells.items():
        chart_store_row = chart_store_by_id.get(tag)
        if chart_store_row is None:
            continue
        chart_image_bytes = _render_chart_store_chart_preview(
            chart_store_row, rect, workfile_state, full_unit_set
        )
        if chart_image_bytes is None:
            continue
        chart_svg_text = _embed_font_in_svg(chart_image_bytes.read().decode("utf-8"), default_font)
        b64 = base64.b64encode(chart_svg_text.encode("utf-8")).decode("ascii")
        x_pct = (rect["x"] / width_emu) * 100
        y_pct = (rect["y"] / height_emu) * 100
        w_pct = (rect["width"] / width_emu) * 100
        h_pct = (rect["height"] / height_emu) * 100
        inserts.append(
            f'<image x="{x_pct}%" y="{y_pct}%" width="{w_pct}%" height="{h_pct}%" '
            f'xlink:href="data:image/svg+xml;base64,{b64}" preserveAspectRatio="none" />'
        )

    if not inserts:
        return table_svg_text
    idx = table_svg_text.rfind("</svg>")
    if idx == -1:
        return table_svg_text
    return table_svg_text[:idx] + "".join(inserts) + table_svg_text[idx:]
