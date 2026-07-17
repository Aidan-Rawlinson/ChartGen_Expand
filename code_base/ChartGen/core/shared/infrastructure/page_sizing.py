"""
page_sizing.py
Conversion between the Charts sandbox's user-facing size unit — a percentage
of the associated PowerPoint page's shorter dimension — and the raw EMU
values stored on the Running Order (width_emu/height_emu). The shorter
dimension is used as the reference so a chart's felt size stays consistent
regardless of whether the page is portrait or landscape.

This is a Charts-sandbox concern only. It has no bearing on how a chart is
actually rendered or inserted at batch run time (assembly_engine.py's own
internal EMU-to-render-resolution conversion is unrelated and untouched).
"""


def _reference_emu(page_width_emu: int, page_height_emu: int) -> int:
    """Return the shorter of the two page dimensions, in EMU."""
    return min(int(page_width_emu), int(page_height_emu))


def percent_to_emu(percent_value: float, page_width_emu: int, page_height_emu: int) -> int:
    """Convert a percent-of-shorter-page-dimension value to an EMU value."""
    ref = _reference_emu(page_width_emu, page_height_emu)
    return int(round((float(percent_value) / 100.0) * ref))


def emu_to_percent(emu_value: int, page_width_emu: int, page_height_emu: int) -> float:
    """Convert an EMU value back to percent-of-shorter-page-dimension."""
    ref = _reference_emu(page_width_emu, page_height_emu)
    if not ref:
        return 0.0
    return (float(emu_value) / ref) * 100.0


# Standard page sizes, in EMU (914400 EMU = 1 inch; 360000 EMU = 1cm).
# Offered as a manual Charts-sheet choice only when no template has been
# processed yet, so no real page size is known — hidden once one is.
STANDARD_PAGE_SIZES_EMU = {
    "A4 (portrait, 21.0 x 29.7cm)":     (7560000, 10692000),
    "A4 (landscape, 29.7 x 21.0cm)":    (10692000, 7560000),
    "4:3 widescreen (10 x 7.5in)":      (9144000, 6858000),
    "16:9 widescreen (13.33 x 7.5in)":  (12192000, 6858000),
}

DEFAULT_STANDARD_PAGE_SIZE = "A4 (portrait, 21.0 x 29.7cm)"


def get_page_size_emu(settings: dict, manual_choice_label: str = None) -> tuple:
    """
    Resolve the page size to use for percent<->EMU conversion, in EMU.

    Real template page size (settings) always wins once known. Falls back to
    the manual dropdown choice, then the default standard size, for the case
    where no template has been processed yet.
    """
    real_w = settings.get("template_page_width_emu")
    real_h = settings.get("template_page_height_emu")
    if real_w and real_h:
        try:
            return int(real_w), int(real_h)
        except (TypeError, ValueError):
            pass

    label = manual_choice_label or DEFAULT_STANDARD_PAGE_SIZE
    return STANDARD_PAGE_SIZES_EMU.get(label, STANDARD_PAGE_SIZES_EMU[DEFAULT_STANDARD_PAGE_SIZE])


def has_known_template_page_size(settings: dict) -> bool:
    """True once a real template page size has been captured in settings."""
    return bool(settings.get("template_page_width_emu")) and bool(settings.get("template_page_height_emu"))
