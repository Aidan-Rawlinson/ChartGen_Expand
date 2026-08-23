"""
submission_codes.py
Normalisation for NHS submission codes.

The API returns codes in LETTER-LETTER-NNN form but pads the numeric part
inconsistently, sometimes right-padding with spaces instead of left-padding
with zeros: "PH50 " where it means "PH050".

Apply this anywhere a raw submissionCode becomes a ChartGen unit_code.
"""

import re

_PATTERN = re.compile(r"^([A-Za-z]{2})(\d+)$")


def normalise_submission_code(raw) -> str:
    """
    Correct a raw submissionCode into LETTER-LETTER-NUMBER-NUMBER-NUMBER
    form. Trims whitespace, then re-pads a two-letters-plus-digits code to
    a minimum 3-digit numeric part (numbers already 3+ digits are left as
    they are, not truncated). Codes that don't match this pattern (blank,
    or a different shape entirely) are returned stripped but otherwise
    unchanged, rather than guessed at.
    """
    code = str(raw or "").strip()
    if not code:
        return code
    match = _PATTERN.match(code)
    if not match:
        return code
    letters, digits = match.groups()
    return f"{letters}{int(digits):03d}"
