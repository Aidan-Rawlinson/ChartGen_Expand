"""
report_context.py
Per-report identity context, rebuilt fresh for each unit in a batch run.
Split out of local_config.py — a domain model, not session or peer-group logic.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReportContext:
    """
    Runtime context for a single report in a batch run.
    Constructed by the Assembly Engine; passed to render_chart.
    """
    unit_id:            str
    unit_code:          str
    unit_name:          str


def build_report_context(settings: dict, units: list) -> Optional[ReportContext]:
    """
    Build a ReportContext from settings and the master table's rows.
    Returns None if no unit is selected or the selected ID is not found.
    """
    selected_id = str(settings.get("selected_unit_id", "") or "").strip()
    if not selected_id:
        return None

    row = next((r for r in units if str(r["unit_id"]) == selected_id), None)
    if row is None:
        return None

    return ReportContext(
        unit_id=str(row["unit_id"]),
        unit_code=row["unit_code"],
        unit_name=row["unit_name"],
    )
