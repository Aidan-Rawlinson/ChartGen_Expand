"""
bundled_fonts.py
The fonts ChartGen ships with itself, in the repo-root (installed-root)
fonts/ folder. One subfolder per family, each holding that family's static
font files and the licence text that came with them.

    fonts/
      inter/
        Inter-Regular.ttf
        Inter-Bold.ttf
        OFL.txt

The subfolder-per-family layout exists so each licence file sits beside its
own font rather than several downloads' licence files colliding on one
name. Nothing here reads the licence; it is reported so the obligation to
ship it stays visible.

A family name is read out of the font file itself, never inferred from the
filename, because the two need not agree and it is the name inside the file
that matplotlib matches on and that gets written into the SVG.

Registering a file with matplotlib (register_with_matplotlib) makes it
usable for this process only. No filesystem or registry change, no admin
rights. That is separate from installing it into Windows, which is what
PowerPoint needs and which lives in session_shell/lifecycle/font_install.py.

Adding a font is dropping files in a folder. Nothing here or anywhere else
needs editing for a new family to appear in the picker.
"""

import os

from matplotlib import font_manager

# fonts/ sits beside chartgen/, both at the repo root and in an installed
# copy ({app}\fonts and {app}\chartgen), so one relative path covers both.
_FONTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "fonts")
)

# Font file types Windows installs and matplotlib reads. OpenType is here
# because it costs nothing to accept and its absence would be a puzzling
# silent omission for whoever drops one in the folder.
_FONT_EXTENSIONS = (".ttf", ".otf")

# The default font written into a brand-new workfile's settings scaffold,
# so a new workfile can render before anyone visits the Settings tab.
#
# A starting value, not a fallback: nothing re-reads this when a workfile's
# own value is missing or names a font this machine does not have. Changing
# the font for a workfile is a Settings tab action and never a code change.
# This one string is the exception, and it governs new workfiles only.
#
# It must name a family that is actually bundled. If the contents of fonts/
# change, change this with them - the Settings tab says plainly when a
# workfile names a font that is not bundled, so a mismatch is visible
# rather than silent, but a new workfile would open unable to render.
#
# "Inter 18pt" rather than "Inter" because Inter has an optical-size axis,
# and Google Fonts' static export instances it at 18pt, 24pt and 28pt and
# names each cut as its own family. 18pt is the cut meant for body text,
# which is what charts and tables draw.
NEW_WORKFILE_FONT = "Inter 18pt"


def fonts_dir() -> str:
    """Absolute path to the bundled fonts folder, whether or not it exists."""
    return _FONTS_DIR


def bundled_font_paths() -> list:
    """
    Every bundled font file, sorted. Empty if the folder is absent or holds
    none - during development that is a legitimate state, not an error, and
    it surfaces on the Settings tab as no bundled fonts found.
    """
    if not os.path.isdir(_FONTS_DIR):
        return []

    paths = []
    for root, _dirs, files in os.walk(_FONTS_DIR):
        for name in files:
            if name.lower().endswith(_FONT_EXTENSIONS):
                paths.append(os.path.join(root, name))
    return sorted(paths)


def read_family_name(path: str) -> str:
    """
    The family name recorded inside the font file - the name matplotlib
    matches on and the name written into the SVG. Not derived from the
    filename, which need not agree with it.
    """
    return font_manager.get_font(path).family_name


def read_style_name(path: str) -> str:
    """The face's style as the file records it, e.g. Regular, Bold, Italic."""
    return font_manager.get_font(path).style_name


def bundled_families() -> dict:
    """
    {family_name: [font file path, ...]}, each list sorted. Several files
    map to one family: Inter-Regular.ttf and Inter-Bold.ttf are both Inter,
    and matplotlib picks between them per element from the weight and style
    asked for at draw time.
    """
    families = {}
    for path in bundled_font_paths():
        families.setdefault(read_family_name(path), []).append(path)
    return {family: sorted(paths) for family, paths in sorted(families.items())}


def bundled_family_names() -> list:
    """The families available to pick as a workfile's default font, sorted."""
    return list(bundled_families().keys())


def register_with_matplotlib() -> list:
    """
    Make every bundled font file usable by matplotlib in this process, and
    return the family names registered.

    addfont clears matplotlib's own font cache, so this can run at any point
    before the first render rather than having to precede any import.
    """
    for path in bundled_font_paths():
        font_manager.fontManager.addfont(path)
    return bundled_family_names()


def licence_files(family: str) -> list:
    """
    Filenames of the licence text found beside a family's font files.

    Reported, never enforced. Shipping the licence with the font is a real
    obligation under the SIL Open Font License and most other font licences,
    but refusing to render over a missing text file would be absurd, so this
    surfaces on the Settings tab and stops nothing.
    """
    paths = bundled_families().get(family, [])
    folders = sorted({os.path.dirname(p) for p in paths})

    found = []
    for folder in folders:
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith((".txt", ".md")) and name not in found:
                found.append(name)
    return found


def has_bold_face(family: str) -> bool:
    """
    Whether asking for bold in this family gets a genuinely different face.

    Asked of matplotlib rather than inferred from style names, because this
    is exactly the question a render asks and the answer is what it acts on.

    A family shipped as a single variable font file answers False. Matplotlib
    reads only a variable font's default instance and cannot walk its weight
    axis, so a request for bold resolves back to the regular face, comes out
    at regular weight, and is reported only as a log line nobody sees.
    ChartGen asks for bold in several places, so this needs to be visible on
    the Settings tab before it reaches a report.
    """
    regular = font_manager.FontProperties(family=family, weight="normal")
    bold = font_manager.FontProperties(family=family, weight="bold")
    try:
        return (font_manager.findfont(bold, fallback_to_default=False)
                != font_manager.findfont(regular, fallback_to_default=False))
    except ValueError:
        return False


def bundled_font_report() -> list:
    """
    One row per bundled family, for the Settings tab: the family name, each
    face found with its style, and the licence files sitting beside them.

    Listing the faces individually, and reporting has_bold separately, is
    deliberate. A family shipped as a single variable font file registers as
    one face at its default weight, and matplotlib cannot walk a variable
    font's weight axis, so a request for bold silently resolves back to
    regular. This is what makes that visible before it reaches a report.

    Reports what is on disk and what matplotlib can do with it. Whether
    Windows has the font installed, which is what PowerPoint needs, is a
    separate question answered by session_shell/lifecycle/font_install.py.
    """
    report = []
    for family, paths in bundled_families().items():
        report.append({
            "family": family,
            "faces": [
                {
                    "path":  path,
                    "file":  os.path.basename(path),
                    "style": read_style_name(path),
                }
                for path in paths
            ],
            "licence_files": licence_files(family),
            "has_bold":      has_bold_face(family),
        })
    return report
