"""
table_naming.py
Naming convention for the population table built from Indicators toolkit
data. No year component: this toolkit has periods, not years, and one fetch
response spans every period at once.
"""


def submissions_timeseries_table_name(project_id) -> str:
    """Table name for an Indicators project's timeseries submissions table."""
    return f"submissions_timeseries_{project_id}"
