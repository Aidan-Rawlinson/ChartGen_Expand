"""
Tests for shared/infrastructure/page_sizing.py

Percent is a widget-only unit (ui/CLAUDE.md). The user types a percentage,
the Running Order stores EMU, and this module is the only bridge. Two things
matter enough to pin down.

First, the reference dimension is the *shorter* page side, so a size means
the same thing on a portrait or a landscape page. If that ever silently
became width, every chart on a landscape template would change size with no
error anywhere.

Second, the Sizing box is a save-back surface: whatever it shows gets
committed to the row on the next save. ui/CLAUDE.md is emphatic that it must
show the real converted value however small or surprising, and that
substituting a plausible-looking default is a defect rather than a
safeguard. So the conversions must not clamp.
"""

from chartgen.shared.infrastructure.page_sizing import (
    DEFAULT_STANDARD_PAGE_SIZE,
    STANDARD_PAGE_SIZES_EMU,
    emu_to_percent,
    get_page_size_emu,
    has_known_template_page_size,
    percent_to_emu,
)

A4_PORTRAIT = (7560000, 10692000)     # shorter side is the width
A4_LANDSCAPE = (10692000, 7560000)    # shorter side is the height


# ---------------------------------------------------------------------------
# The shorter dimension is the reference
# ---------------------------------------------------------------------------

def test_fifty_percent_of_a4_portrait_is_half_the_width():
    assert percent_to_emu(50.0, *A4_PORTRAIT) == 3780000


def test_the_same_percentage_gives_the_same_emu_on_portrait_and_landscape():
    """
    The point of using the shorter side. A chart authored at 40% keeps its
    real size if the template is later rotated.
    """
    assert percent_to_emu(40.0, *A4_PORTRAIT) == percent_to_emu(40.0, *A4_LANDSCAPE)


def test_one_hundred_percent_is_the_whole_shorter_side():
    assert percent_to_emu(100.0, *A4_PORTRAIT) == 7560000


def test_zero_percent_is_zero_emu():
    assert percent_to_emu(0.0, *A4_PORTRAIT) == 0


# ---------------------------------------------------------------------------
# Round-tripping, including the values the UI must not tidy up
# ---------------------------------------------------------------------------

def test_converting_to_emu_and_back_returns_the_original_percentage():
    for pct in [0.03, 1.0, 12.5, 50.0, 70.0, 99.99]:
        there_and_back = emu_to_percent(percent_to_emu(pct, *A4_PORTRAIT), *A4_PORTRAIT)
        assert round(there_and_back, 2) == pct


def test_a_tiny_stored_size_converts_to_a_tiny_percentage_and_is_not_rounded_up():
    """
    ui/CLAUDE.md: "A stored size that converts to 0.03% displays as 0.03%,
    because that is what is stored." Anything that quietly returned a more
    plausible number here would get committed to the row on the next save.
    """
    tiny_emu = percent_to_emu(0.03, *A4_PORTRAIT)
    assert round(emu_to_percent(tiny_emu, *A4_PORTRAIT), 2) == 0.03


def test_a_size_larger_than_the_page_is_reported_as_over_one_hundred_percent():
    """
    The widget deliberately carries no upper bound: a user may set a size
    that runs off the page, and that is their choice. Clamping it here would
    reintroduce exactly the defect ui/CLAUDE.md warns about.
    """
    assert emu_to_percent(15120000, *A4_PORTRAIT) == 200.0


def test_a_zero_page_size_reports_zero_percent_rather_than_dividing_by_zero():
    assert emu_to_percent(500000, 0, 0) == 0.0


# ---------------------------------------------------------------------------
# get_page_size_emu precedence
# ---------------------------------------------------------------------------

def test_the_real_template_page_size_wins_over_any_manual_choice():
    settings = {"template_page_width_emu": 1234567, "template_page_height_emu": 7654321}
    assert get_page_size_emu(settings, "4:3 widescreen (10 x 7.5in)") == (1234567, 7654321)


def test_the_manual_choice_is_used_when_no_template_has_been_processed():
    assert get_page_size_emu({}, "A4 (landscape, 29.7 x 21.0cm)") == A4_LANDSCAPE


def test_the_default_standard_size_is_used_when_there_is_nothing_else():
    assert get_page_size_emu({}, None) == STANDARD_PAGE_SIZES_EMU[DEFAULT_STANDARD_PAGE_SIZE]


def test_an_unrecognised_manual_choice_falls_back_to_the_default():
    assert get_page_size_emu({}, "Not a page size") == STANDARD_PAGE_SIZES_EMU[DEFAULT_STANDARD_PAGE_SIZE]


def test_an_unusable_stored_template_size_falls_back_rather_than_raising():
    """
    A non-numeric value in settings should not take down the Sizing box on
    every render.
    """
    settings = {"template_page_width_emu": "not a number", "template_page_height_emu": "also not"}
    assert get_page_size_emu(settings, None) == STANDARD_PAGE_SIZES_EMU[DEFAULT_STANDARD_PAGE_SIZE]


def test_a_partially_recorded_template_size_is_not_treated_as_known():
    """Width alone is not enough to convert anything."""
    assert has_known_template_page_size({"template_page_width_emu": 7560000}) is False


def test_a_template_size_is_known_only_once_both_dimensions_are_recorded():
    assert has_known_template_page_size({}) is False
    assert has_known_template_page_size(
        {"template_page_width_emu": 7560000, "template_page_height_emu": 10692000}
    ) is True
