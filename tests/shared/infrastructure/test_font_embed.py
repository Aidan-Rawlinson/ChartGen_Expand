"""
Tests for shared/infrastructure/font_embed.py

font_face_css exists because the browser rendering a preview SVG is a
different text engine from matplotlib, with its own font lookup on the
machine it runs on -- nothing that makes a font available to matplotlib or
to PowerPoint reaches it. The promise worth protecting is that the CSS it
returns actually lets a browser draw the family it names: one @font-face
rule per bundled face, embedding that face's own bytes, under the
font-weight/font-style a browser would need to pick the right one, using
read_style_name rather than re-deriving anything from the filename.

These tests build a fonts folder out of the .ttf files matplotlib ships in
its own package, rather than committing font binaries into the repo -- the
same approach test_bundled_fonts.py uses.
"""

import base64
import os
import shutil

import pytest
from matplotlib import font_manager

from chartgen.shared.infrastructure import bundled_fonts, font_embed
from chartgen.shared.infrastructure.font_embed import font_face_css

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
    Builds a fonts folder from matplotlib's own .ttf files, points
    bundled_fonts at it, and clears font_face_css's cache so each test
    starts from a clean slate rather than a previous test's cached result.
    """
    def _build(families):
        root = tmp_path / "fonts"
        root.mkdir(parents=True, exist_ok=True)
        for subfolder, filenames in families.items():
            folder = root / subfolder
            folder.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                shutil.copy(mpl_ttf(filename), folder / filename)
        monkeypatch.setattr(bundled_fonts, "_FONTS_DIR", str(root))
        font_face_css.cache_clear()
        return root
    return _build


def test_an_unbundled_family_returns_nothing_rather_than_raising(fonts_folder):
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]})

    assert font_face_css("No Such Font Anywhere") == ""


def test_one_face_produces_one_font_face_rule_naming_the_family(fonts_folder):
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]})

    css = font_face_css("DejaVu Sans")

    assert css.startswith("<style>") and css.endswith("</style>")
    assert css.count("@font-face") == 1
    assert 'font-family:"DejaVu Sans"' in css


def test_several_faces_each_get_their_own_rule(fonts_folder):
    """
    Regular and Bold are two files under one family -- the browser needs a
    separate @font-face per face to ever draw the bold one correctly.
    """
    fonts_folder({"dejavu": ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]})

    css = font_face_css("DejaVu Sans")

    assert css.count("@font-face") == 2
    assert "font-weight:bold" in css
    assert "font-weight:normal" in css


def test_a_bold_face_is_declared_bold_not_normal(fonts_folder):
    """
    The style comes from read_style_name, the same source ChartGen already
    trusts elsewhere -- not re-derived from the filename, which need not
    agree with it.
    """
    fonts_folder({"dejavu": ["DejaVuSans-Bold.ttf"]})

    css = font_face_css("DejaVu Sans")

    assert "font-weight:bold;font-style:normal" in css


def test_the_embedded_bytes_are_the_actual_font_file(fonts_folder, mpl_ttf):
    """
    The whole point: what's embedded has to be bytes a browser can actually
    render the family from, not a placeholder or a truncated read.
    """
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]})
    expected = base64.b64encode(open(mpl_ttf("DejaVuSans.ttf"), "rb").read()).decode("ascii")

    css = font_face_css("DejaVu Sans")

    assert expected in css


def test_repeated_calls_for_the_same_family_are_cached(fonts_folder, monkeypatch):
    """
    Re-reading and re-encoding the same files on every Streamlit rerun
    would be pure waste -- lru_cache is what avoids it.
    """
    fonts_folder({"dejavu": ["DejaVuSans.ttf"]})
    first = font_face_css("DejaVu Sans")

    read_calls = []
    real_open = open

    def counting_open(path, *args, **kwargs):
        if str(path).endswith(".ttf"):
            read_calls.append(path)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(font_embed, "open", counting_open, raising=False)

    second = font_face_css("DejaVu Sans")

    assert second == first
    assert read_calls == []
