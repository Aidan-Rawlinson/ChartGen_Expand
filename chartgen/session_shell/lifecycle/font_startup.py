"""
font_startup.py
Makes ChartGen's bundled fonts usable, once per session, in the two separate
senses that matter.

**Registered with matplotlib.** Process-only, no filesystem or registry
change, no admin rights. This is what makes charts and tables draw in the
font. bundled_fonts.register_with_matplotlib does it.

**Installed into Windows.** This is what PowerPoint needs. Base Charts emit
SVG with svg.fonttype = "none", so text stays real <text> and the font
family *name* is what lands in the deck. PowerPoint resolves that name
against locally installed fonts and substitutes on its own terms if it
cannot. A font registered only with matplotlib is invisible to it.

The install is per user: the file goes to %LOCALAPPDATA%\\Microsoft\\Windows\\
Fonts and the registry value to HKCU, which is what "Install for me only"
does in the Windows font viewer. No admin rights and no UAC prompt,
consistent with the installer's own PrivilegesRequired=lowest and HKCU-only
design.

## What is checked, and what that claim means

The check asks whether *our* font file is installed: is a file of that name
present in the per-user or system fonts folder, and does a registry value
point at it. Nothing more. It deliberately does not try to answer "is this
family installed by any route", which would mean opening several hundred
font files on every startup to compare the family name inside each against
the registry's friendly label, since the two need not agree.

The cost of the narrower question is one harmless case: a family already
pushed to the machine by other means, under a different filename, is not
recognised, and ChartGen installs its own per-user copy alongside. Same
font, one redundant file. Worth it to keep startup cheap and the claim
precise.

## Writes are rare

The check is a few file-existence tests and a registry read on every start.
A write happens only when a font is genuinely absent, so in practice once
per machine per font file, not once per launch.

## Two accepted consequences

A per-user font installed from here persists after ChartGen is uninstalled,
because the uninstaller has no record of it.

AddFontResourceW affects only the calling process, and an already-running
PowerPoint may not pick up a newly installed font until it restarts. So the
first PDF export after a font is installed can still substitute, even though
the .pptx itself is correct. Installing at startup, before PowerPoint is
opened by a report run, makes that rare rather than routine.
"""

import ctypes
import os
import shutil

import streamlit as st

from chartgen.shared.infrastructure import bundled_fonts

try:
    import winreg
except ImportError:
    winreg = None  # allows this module to import on a machine without winreg

_FONTS_REGISTRY_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"

# Windows' own friendly-name convention for a font registry value, e.g.
# "Inter (TrueType)", "Inter Bold (TrueType)". Constructed from the family
# and style read out of the file rather than from the filename.
_TYPE_SUFFIXES = {".ttf": "(TrueType)", ".otf": "(OpenType)"}

_HWND_BROADCAST = 0xFFFF
_WM_FONTCHANGE = 0x001D
_SMTO_ABORTIFHUNG = 0x0002


def per_user_fonts_dir() -> str:
    """Where a no-admin font install puts the file."""
    return os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"
    )


def system_fonts_dir() -> str:
    """Where a machine-wide install puts it, checked so we never duplicate one."""
    return os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Fonts")


def registry_value_name(path: str) -> str:
    """
    The friendly name Windows lists a font under, built from the family and
    style inside the file. A Regular face is listed under the family name
    alone, matching how Windows itself names them.
    """
    family = bundled_fonts.read_family_name(path)
    style = bundled_fonts.read_style_name(path)
    suffix = _TYPE_SUFFIXES.get(os.path.splitext(path)[1].lower(), "(TrueType)")

    if style.strip().lower() in ("regular", "book", ""):
        return f"{family} {suffix}"
    return f"{family} {style} {suffix}"


def _registered_filename(value_name: str) -> str:
    """
    The font filename the registry holds under this friendly name, from the
    per-user key first and then the machine-wide one, lowercased. Empty if
    neither key has it.

    A direct lookup rather than an enumeration. The friendly name is
    constructed the same way Windows constructs it, so it can be asked for
    by name; enumerating instead meant reading several hundred values, and
    since st.tabs runs every tab's body on every rerun, the Settings tab
    would have charged that to every interaction anywhere in ChartGen.
    """
    if winreg is None:
        return ""

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, _FONTS_REGISTRY_KEY) as key:
                data, _type = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue
        if isinstance(data, str) and data:
            return os.path.basename(data).lower()
    return ""


def is_font_file_installed(path: str) -> bool:
    """
    Whether this bundled font file is installed in Windows: the file is
    present in the per-user or system fonts folder, and a registry value
    points at a file of that name.

    Both halves are required. A file copied in without a registry value is
    not a font as far as Windows is concerned, and a registry value with no
    file behind it is a broken entry.
    """
    filename = os.path.basename(path)

    present = (
        os.path.exists(os.path.join(per_user_fonts_dir(), filename))
        or os.path.exists(os.path.join(system_fonts_dir(), filename))
    )
    return present and _registered_filename(registry_value_name(path)) == filename.lower()


def install_font_file(path: str) -> str:
    """
    Install one font file for the current user. Returns "" on success, or a
    plain-English description of what went wrong.

    Three steps, in the order Windows expects: copy the file, write the
    registry value that makes it a font rather than a stray file, then tell
    the running system about it.

    AddFontResourceW only affects this process; the registry value is what
    reaches PowerPoint, and the WM_FONTCHANGE broadcast is what lets
    already-running applications notice without a restart. Neither failing
    is fatal to the install, so both are reported rather than raised - the
    file and the registry value are what persist.
    """
    if winreg is None:
        return "This machine has no Windows registry support, so fonts cannot be installed."

    filename = os.path.basename(path)
    dest_dir = per_user_fonts_dir()
    if not dest_dir or not os.environ.get("LOCALAPPDATA"):
        return "LOCALAPPDATA is not set, so there is nowhere to install a per-user font."

    dest = os.path.join(dest_dir, filename)

    try:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copyfile(path, dest)
    except OSError as e:
        return f"Could not copy {filename} to {dest_dir}: {e}"

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _FONTS_REGISTRY_KEY) as key:
            winreg.SetValueEx(key, registry_value_name(path), 0, winreg.REG_SZ, dest)
    except OSError as e:
        return (
            f"Copied {filename} but could not register it with Windows: {e}. "
            "A managed machine may block per-user font installation by policy."
        )

    if ctypes.windll.gdi32.AddFontResourceW(ctypes.c_wchar_p(dest)) == 0:
        return (
            f"Installed {filename}, but Windows did not load it into this "
            "session. It should be available after ChartGen is restarted."
        )

    ctypes.windll.user32.SendMessageTimeoutW(
        _HWND_BROADCAST, _WM_FONTCHANGE, 0, None, _SMTO_ABORTIFHUNG, 1000, None
    )
    return ""


def font_status() -> list:
    """
    One row per bundled family for the Settings tab, joining what is on disk
    and known to matplotlib with what Windows has installed.

    Each row is bundled_fonts.bundled_font_report()'s row plus:
        installed -- every face of this family is installed in Windows
        missing   -- the faces that are not, by filename
    """
    rows = []
    for row in bundled_fonts.bundled_font_report():
        missing = [
            face["file"] for face in row["faces"]
            if not is_font_file_installed(face["path"])
        ]
        rows.append(dict(row, installed=(not missing), missing=missing))
    return rows


def install_missing_fonts() -> list:
    """
    Install every bundled font file Windows does not already have. Returns a
    list of plain-English problem descriptions, empty when everything either
    installed cleanly or was already there.

    Nothing already installed is touched, so this is a no-op on all but the
    first run on a machine.
    """
    problems = []
    for path in bundled_fonts.bundled_font_paths():
        if is_font_file_installed(path):
            continue
        problem = install_font_file(path)
        if problem:
            problems.append(problem)
    return problems


def apply_font_startup():
    """
    On the first run of the session only, register the bundled fonts with
    matplotlib and install into Windows anything missing.

    Streamlit reruns the whole script on every interaction, so this must not
    re-trigger - the same session gate startup_file.py uses.

    Install problems are stashed for app.py to show. A font that could not be
    installed is still registered with matplotlib, so charts render correctly
    and only PowerPoint is affected; that is worth saying out loud rather
    than leaving to be discovered in a finished report.
    """
    if st.session_state.get("fonts_checked"):
        return
    st.session_state["fonts_checked"] = True

    bundled_fonts.register_with_matplotlib()

    problems = install_missing_fonts()
    if problems:
        st.session_state["font_install_problems"] = problems
