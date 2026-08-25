"""
report_tags.py
The report level text tags: one list, REPORT_TEXT_TAGS, that is the definition
of them rather than a description of behaviour written elsewhere.

Everything that shows these tags or acts on them reads this list: the Text
tab's table, update_text, and Output Table cell resolution. Nothing names a
tag or a description of its own. Removing an entry here therefore stops that
replacement happening anywhere, and adding one makes it appear in the Text tab
and work in the same change.

A tag resolves against the ReportContext for the report being generated, so a
per-unit value is rebuilt for each unit in a batch run. A run-time value such
as the current date takes no notice of it.

[code] is also an image-path token in insert_picture, substituted there from
the same ReportContext field by its own separate mechanism. The two never
meet — update_text walks slide text, insert_picture rewrites a Running Order
path — but removing the entry here would not stop that one.
"""

from datetime import date


def _format_date(d: date) -> str:
    """
    "5 August 2026" — day, full month name, year, with no leading zero on the
    day. Built from d.day rather than a strftime directive because the
    no-padding directives (%-d, %#d) are platform specific.
    """
    return f"{d.day} {d:%B %Y}"


def _format_month(d: date) -> str:
    """"August 2026" — full month name and year."""
    return f"{d:%B %Y}"


REPORT_TEXT_TAGS = [
    {
        "tag": "[selected-reporting-unit-name]",
        "description": "Unit name",
        "resolve": lambda rc: (rc.unit_name or "") if rc else None,
    },
    {
        "tag": "[code]",
        "description": "Unit code",
        "resolve": lambda rc: (rc.unit_code or "") if rc else None,
    },
    {
        "tag": "[date]",
        "description": "Current Date",
        "resolve": lambda rc: _format_date(date.today()),
    },
    {
        "tag": "[month]",
        "description": "Current Month",
        "resolve": lambda rc: _format_month(date.today()),
    },
]


def build_report_tag_tokens(report_context) -> dict:
    """
    Resolve every report level tag for this report, keyed by its literal
    template text. A tag whose resolve returns None cannot be resolved for
    this report — with no reporting unit selected there is no unit name — and
    is omitted, leaving its literal text untouched rather than replacing it
    with something misleading. The same convention build_stat_tag_tokens
    follows.
    """
    tokens = {}
    for entry in REPORT_TEXT_TAGS:
        value = entry["resolve"](report_context)
        if value is None:
            continue
        tokens[entry["tag"]] = value
    return tokens
