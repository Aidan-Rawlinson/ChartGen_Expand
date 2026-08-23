"""
table_naming.py
Naming convention for the population tables built from NHS toolkit data.
NHS-specific: another database has its own convention.
"""


def submissions_table_name(year, project_id) -> str:
    """Table name for a project/year's submissions table."""
    return f"submissions_{year}_{project_id}"
