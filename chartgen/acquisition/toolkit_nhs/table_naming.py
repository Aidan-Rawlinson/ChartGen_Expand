"""
table_naming.py
Naming convention for the population tables built from nhs toolkit data.
nhs-specific: a different database will have its own naming convention, not
necessarily this one. Kept separate from new_workfile.py (which builds the
tables) so acquisition.toolkit_nhs.fetch can also use it, without acquisition
code depending on workfile.setup.
"""


def submissions_table_name(year, project_id) -> str:
    """Table name for a project/year's submissions table."""
    return f"submissions_{year}_{project_id}"
