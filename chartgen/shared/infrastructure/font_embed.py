"""
font_embed.py
A bundled font family, as a browser-usable @font-face CSS block.

The Streamlit preview injects a Base Chart or Base Table's SVG straight into
the page as markup, so it is the browser's own SVG/text engine that draws
the <text> elements in it -- a different renderer from matplotlib, doing its
own font lookup on the machine it runs on. Nothing installed for matplotlib
(bundled_fonts.register_with_matplotlib) or for PowerPoint
(session_shell/lifecycle/font_startup.py) reaches that renderer, so the
family named in the SVG can go unresolved there even when both of those
succeeded.

font_face_css embeds the font's own bytes into the page instead, so the
browser never has to find the family on the machine at all.
"""

import base64
import functools
import os

from chartgen.shared.infrastructure.bundled_fonts import bundled_families, read_style_name


@functools.lru_cache(maxsize=None)
def font_face_css(family: str) -> str:
    """
    A <style> block declaring one @font-face rule per bundled face of
    `family`, each face's file embedded as a base64 data URI under its own
    font-weight/font-style, all sharing `family` as the CSS font-family
    name -- the same name the SVG's own text elements carry, so the browser
    matches them without needing the font installed anywhere on the machine.

    font-weight/font-style come from read_style_name, the same style
    ChartGen already reads for every other purpose, never re-derived from
    the filename.

    Cached on family, since the bundled files do not change during a run
    and re-reading and re-encoding them on every Streamlit rerun would be
    pure waste.

    Returns "" for a family with no bundled faces. In practice that cannot
    happen: the Settings tab offers only bundled families, and render_font
    already refuses to render a family that is not available before this
    function would ever be reached for it.
    """
    paths = bundled_families().get(family, [])
    rules = []
    for path in paths:
        style_name = read_style_name(path).lower()
        weight = "bold" if "bold" in style_name else "normal"
        style = "italic" if "italic" in style_name or "oblique" in style_name else "normal"
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        fmt = "opentype" if ext == "otf" else "truetype"
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        rules.append(
            "@font-face {"
            f'font-family:"{family}";'
            f"font-weight:{weight};"
            f"font-style:{style};"
            f'src:url(data:font/{ext};base64,{encoded}) format("{fmt}");'
            "}"
        )

    if not rules:
        return ""
    return "<style>" + "".join(rules) + "</style>"
