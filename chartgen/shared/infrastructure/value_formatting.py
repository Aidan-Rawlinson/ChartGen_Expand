"""
value_formatting.py
Numeric display formatting, shared by the UI and by generation-time text
substitution.

ui.common.formatting re-exports format_number, so a rename here has two
call sites.
"""


def format_number(value, format_modifier):
    """
    Format a scalar value per a data shape's format_modifier, Excel-style:
    no modifier -> comma-thousands, no decimals ("#,###"); "P" -> the same
    plus a "%" suffix ("#,##0%"); "C" -> the same with a "£" prefix
    ("£#,##0"). Values are not rescaled — this only controls display.
    Returns "" for None.

    Base Chart functions carry their own copy of this logic, since they
    import nothing from ChartGen.
    """
    if value is None:
        return ""
    if format_modifier == "P":
        return f"{value:,.0f}%"
    if format_modifier == "C":
        return f"£{value:,.0f}"
    return f"{value:,.0f}"


def format_reference_value(value, kind, format_modifier):
    """
    Format one summary-stats Reference-id row's value (shapes/reference_ids.py)
    per its "kind": "count" is always a plain integer; "percent" is always
    shown as a %, regardless of format_modifier; "value" respects
    format_modifier the same way a chart itself does (£, %, or plain).
    Used by the Charts sheet display and by stat tags (Text tab / update_text).
    """
    if value is None:
        return ""
    if kind == "count":
        return f"{value:,.0f}"
    if kind == "percent":
        return f"{value:,.1f}%"
    return format_number(value, format_modifier)
