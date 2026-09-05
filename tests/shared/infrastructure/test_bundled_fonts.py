"""
Tests for shared/infrastructure/bundled_fonts.py

This module answers "which fonts does ChartGen ship, and what can matplotlib
actually do with them". Two promises in it are worth protecting, because
breaking either produces a wrong report rather than an error.

The first is that a family name is read out of the font file and never
inferred from the filename. Filenames are whatever the download happened to
call them, and the name inside the file is the one matplotlib matches on and
the one written into the SVG for PowerPoint to resolve. Deriving it from the
filename would look right for Inter-Regular.ttf and be wrong the moment a
file is renamed or arrives oddly named, with no symptom but a font that
cannot be selected.

The second is has_bold_face. A family shipped as a single variable font file
registers as one face at its default weight, matplotlib cannot walk a
variable font's weight axis, and a request for bold therefore resolves back
to the regular face and renders at regular weight. Matplotlib reports that
as a log line nobody sees. ChartGen asks for bold in several places, so this
is exactly the silent substitution the fail-visibly rule exists to catch.

These tests build a fonts folder out of the .ttf files matplotlib ships in
its own package, rather than committing font binaries into the repo.
"""

import os
import shutil

import pytest
from matplotlib import font_manager

from chartgen.shared.infrastructure import bundled_fonts
from chartgen.shared.infrastructure.bundled_fonts import (
    NEW_WORKFILE_FONT,
    bundled_families,
    bundled_family_names,
    bundled_font_paths,
    bundled_font_report,
    has_bold_face,
    licence_files,
    read_family_name,
    read_style_name,
    register_with_matplotlib,
)


# ---------------------------------------------------------------------------
# Fixtures: a bundled fonts folder built from matplotlib's own font files
# ---------------------------------------------------------------------------

_MPL_TTF_DIR = os.path.join(
    os.path.dirname(font_manager.__file__), "mpl-data", "fonts", "ttf"
)


@pytest.fixture
def mpl_ttf():
    """Returns a function giving the path to one of matplotlib's own .ttf files."""
    def _path(filename):
        path = os.path.join(_MPL_TTF_DIR, filename)
        assert os.path.exists(path), "matplotlib no longer ships " + filename
        return path
    return _path


@pytest.fixture
def fonts_folder(tmp_path, monkeypatch, mpl_ttf):
    """
    Returns a function that builds a fonts folder and points the module at
    it, so these tests never depend on what is actually sitting in the
    repo's fonts/ folder.

    families -- {subfolder: [filename, ...]} of matplotlib .ttf files to copy
    licences -- {subfolder: [filename, ...]} of licence text files to create
    """
    def _build(families, licences=None):
        root = tmp_path / "fonts"
        root.mkdir(parents=True, exist_ok=True)
        for subfolder, filenames in families.items():
            folder = root / subfolder
            folder.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                shutil.copy(mpl_ttf(filename), folder / filename)
        for subfolder, filenames in (licences or {}).items():
            folder = root / subfolder
            folder.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                (folder / filename).write_text("licence text", encoding="utf-8")
        monkeypatch.setattr(bundled_fonts, "_FONTS_DIR", str(root))
        return root
    return _build


# ---------------------------------------------------------------------------
# The family name comes from inside the file
# ---------------------------------------------------------------------------

def test_the_family_name_is_read_from_the_file_not_the_filename(tmp_path, mpl_ttf):
    """
    The documented promise, and the one a well-meaning simplification would
    break. A file named anything at all still reports the family recorded
    inside it, because that is the name matplotlib matches on.
    """
    misleading = tmp_path / "NotWhatThisFontIsCalled.ttf"
    shutil.copy(mpl_ttf("DejaVuSans.ttf"), misleading)

    assert read_family_name(str(misleading)) == "DejaVu Sans"


def test_the_style_name_is_read_from_the_file(mpl_ttf):
    assert read_style_name(mpl_ttf("DejaVuSans-Bold.ttf")) == "Bold"


def test_several_files_collapse_into_one_family(fonts_folder):
    """
    Regular and Bold are two files and one family. matplotlib picks between
    them per element from the weight asked for, so the picker must offer the
    family once, not once per file.
    """
    fonts_folder({"dejavu": ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]})

    assert bundled_family_names() == ["DejaVu Sans"]
    assert len(bundled_families()["DejaVu Sans"]) == 2


def test_families_in_separate_folders_are_both_offered(fonts_folder):
    fonts_folder({
        "dejavu-sans":  ["DejaVuSans.ttf"],
        "dejavu-serif": ["DejaVuSerif.ttf"],
    })

    assert bundled_family_names() == ["DejaVu Sans", "DejaVu Serif"]


# ---------------------------------------------------------------------------
# An empty or absent folder is a legitimate state, not an error
# ---------------------------------------------------------------------------

def test_an_absent_fonts_folder_reports_no_fonts_rather_than_failing(tmp_path, monkeypatch):
    """
    During development the folder may not exist yet. That surfaces on the
    Settings tab as no bundled fonts found, which is visible, rather than
    stopping the application from starting.
    """
    monkeypatch.setattr(bundled_fonts, "_FONTS_DIR", str(tmp_path / "nothing-here"))

    assert bundled_font_paths() == []
    assert bundled_family_names() == []
    assert bundled_font_report() == []


def test_a_folder_holding_no_font_files_reports_no_fonts(fonts_folder):
    fonts_folder({}, licences={"inter": ["OFL.txt"]})

    assert bundled_family_names() == []


# ---------------------------------------------------------------------------
# Licence files are reported, never enforced
# ---------------------------------------------------------------------------

def test_the_licence_file_beside_a_family_is_reported(fonts_folder):
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]}, licences={"dejavu": ["OFL.txt"]})

    assert licence_files("DejaVu Sans") == ["OFL.txt"]


def test_a_family_with_no_licence_file_is_still_offered(fonts_folder):
    """
    Shipping the licence with the font is a real obligation, but refusing to
    render over a missing text file would be absurd. It is reported and
    stops nothing.
    """
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]})

    assert licence_files("DejaVu Sans") == []
    assert bundled_family_names() == ["DejaVu Sans"]


# ---------------------------------------------------------------------------
# Bold detection, the variable-font trap
# ---------------------------------------------------------------------------

def test_a_family_shipping_a_bold_face_reports_bold():
    assert has_bold_face("DejaVu Sans") is True


def test_a_family_with_only_one_face_reports_no_bold():
    """
    The case a single variable font file produces: one registered face, so a
    request for bold comes back with the same file and renders at regular
    weight. Reporting False is what makes that visible before it reaches a
    report.
    """
    assert has_bold_face("DejaVu Sans Display") is False


def test_an_unknown_family_reports_no_bold_rather_than_raising():
    assert has_bold_face("No Such Font Anywhere") is False


# ---------------------------------------------------------------------------
# Registration, and the report the Settings tab renders
# ---------------------------------------------------------------------------

def test_registering_makes_every_bundled_family_available_to_matplotlib(fonts_folder):
    """
    The point of registration: a bundled font is usable for this process
    without being installed on the machine, so charts draw correctly even
    where the Windows install has not happened or was refused.
    """
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]})

    registered = register_with_matplotlib()

    assert registered == ["DejaVu Sans"]
    for family in registered:
        assert family in font_manager.fontManager.get_font_names()


def test_the_report_names_each_face_and_whether_bold_is_present(fonts_folder):
    fonts_folder(
        {"dejavu": ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]},
        licences={"dejavu": ["OFL.txt"]},
    )

    report = bundled_font_report()

    assert len(report) == 1
    row = report[0]
    assert row["family"] == "DejaVu Sans"
    assert sorted(face["style"] for face in row["faces"]) == ["Bold", "Book"]
    assert row["licence_files"] == ["OFL.txt"]
    assert row["has_bold"] is True


# ---------------------------------------------------------------------------
# The new-workfile scaffold value
# ---------------------------------------------------------------------------

def test_a_new_workfile_has_a_font_to_start_from():
    """
    NEW_WORKFILE_FONT is the initial value written into a new workfile's
    settings. It is a starting point the user changes, not a fallback -
    nothing re-reads it when a workfile's own value is missing - but it does
    have to be a real name rather than blank, or every new workfile would
    open unable to render.
    """
    assert NEW_WORKFILE_FONT.strip() != ""
