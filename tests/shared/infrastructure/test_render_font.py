"""
Tests for shared/infrastructure/render_font.py

One promise here, and it is the whole reason the module exists: a font that
is not available stops the render instead of being quietly replaced.

Matplotlib's own behaviour is the opposite. Handed a family it cannot find
it substitutes DejaVu Sans and writes a line through the logging module,
which is not a warning, not an exception, cached so it appears at most once
per process, and printed to a console nobody is looking at. Text is kept as
real <text> in the SVG, so the family name also reaches PowerPoint, which
substitutes again on its own terms - so a chart can be laid out against one
font's metrics and displayed in another, in a finished report, with nothing
anywhere saying so.

The tempting change these tests exist to stop is any form of "fall back to
something sensible when the font is missing". A sensible fallback is exactly
the silent wrong report the standing fail-visibly rule forbids.

The second promise, smaller but worth pinning, is that the family is scoped
to the block. rcParams is one process-wide object, so a render that left its
font behind would change every later render in the session.
"""

import matplotlib
import pytest

from chartgen.shared.infrastructure.render_font import font_is_available, render_font


# A family matplotlib always has, since it ships it and falls back to it.
AVAILABLE = "DejaVu Sans"
UNAVAILABLE = "No Such Font Anywhere"


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def test_a_font_matplotlib_holds_is_available():
    assert font_is_available(AVAILABLE) is True


def test_a_font_matplotlib_does_not_hold_is_not_available():
    assert font_is_available(UNAVAILABLE) is False


def test_no_font_name_is_not_available():
    """
    An open workfile with no default font set. Blank is not a wildcard and
    not a request for the default; there is simply nothing to render in.
    """
    assert font_is_available("") is False


# ---------------------------------------------------------------------------
# An unavailable font is refused, never substituted
# ---------------------------------------------------------------------------

def test_an_unavailable_font_is_refused():
    with pytest.raises(ValueError):
        render_font(UNAVAILABLE)


def test_an_unset_font_is_refused():
    with pytest.raises(ValueError):
        render_font("")


def test_the_refusal_happens_before_the_render_starts():
    """
    The check runs when render_font is called, not when the block is
    entered, so the failure lands at the call site rather than part-way
    through a render.
    """
    with pytest.raises(ValueError):
        render_font(UNAVAILABLE)

    with pytest.raises(ValueError):
        with render_font(UNAVAILABLE):
            raise AssertionError("the block must never be entered")


def test_the_refusal_says_which_font_and_where_to_fix_it():
    """
    The message reaches the run log and the preview surfaces, so it has to
    name the font that failed and point at the Settings tab. Without both,
    the error is visible but not actionable.
    """
    with pytest.raises(ValueError) as refused:
        render_font(UNAVAILABLE)

    message = str(refused.value)
    assert UNAVAILABLE in message
    assert "Settings tab" in message


def test_the_unset_refusal_also_points_at_the_settings_tab():
    with pytest.raises(ValueError) as refused:
        render_font("")

    assert "Settings tab" in str(refused.value)


# ---------------------------------------------------------------------------
# An available font is applied, and only for the block
# ---------------------------------------------------------------------------

def test_the_font_is_in_force_inside_the_block():
    with render_font(AVAILABLE):
        assert matplotlib.rcParams["font.family"] == [AVAILABLE]


def test_the_font_is_restored_after_the_block():
    """
    rcParams is process-wide. A render that left its font behind would
    change every later render in the session, including previews of charts
    the user never touched.
    """
    before = matplotlib.rcParams["font.family"]

    with render_font(AVAILABLE):
        pass

    assert matplotlib.rcParams["font.family"] == before


def test_the_font_is_restored_even_when_the_render_raises():
    """
    Base Charts do fail - a metric with no data, a bad tweaks string - and
    the dispatcher turns that into an error result and carries on. The font
    must not survive such a failure into the next render.
    """
    before = matplotlib.rcParams["font.family"]

    with pytest.raises(RuntimeError):
        with render_font(AVAILABLE):
            raise RuntimeError("a render failing part-way through")

    assert matplotlib.rcParams["font.family"] == before


def test_nesting_restores_the_outer_font():
    """
    A table renders, then its chart cells render inside their own wrap. The
    inner one must not leak into the rest of the outer render.
    """
    with render_font("DejaVu Serif"):
        with render_font(AVAILABLE):
            assert matplotlib.rcParams["font.family"] == [AVAILABLE]
        assert matplotlib.rcParams["font.family"] == ["DejaVu Serif"]
