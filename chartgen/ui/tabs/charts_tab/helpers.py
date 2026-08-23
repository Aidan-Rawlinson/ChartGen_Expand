"""
helpers.py
The one helper needed by more than one module in this package.
"""

def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
