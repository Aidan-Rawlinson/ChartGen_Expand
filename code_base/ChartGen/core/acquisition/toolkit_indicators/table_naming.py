"""
table_naming.py
Naming convention for the population table built from Indicators toolkit
data — its own convention, not the NHS side's submissions_{year}_{project_id}
(Architecture/Functional Spec §7.2). No year component: the Indicators
toolkit has periods, not years, and a single fetch response already spans
every period at once — the table isn't partitioned by year at all.
"""


def submissions_timeseries_table_name(project_id) -> str:
    """Table name for an Indicators project's timeseries submissions table."""
    return f"submissions_timeseries_{project_id}"
