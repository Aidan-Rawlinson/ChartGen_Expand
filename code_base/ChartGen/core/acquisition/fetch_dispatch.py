"""
fetch_dispatch.py
Combines every toolkit's own fetch_all into the single Fetch action the
Imports tab calls. Lives outside both toolkit_nhs/ and toolkit_indicators/
— same reason url_triage.py does: something has to know about both without
either toolkit package depending on the other.

Each toolkit's fetch_all already filters to its own rows internally (by the
manifest row's database column); this wraps on_progress with an offset per
phase so the two runs report against one continuous total, rather than the
progress bar restarting from 0 partway through — every URL is treated
identically from the person's point of view, regardless of which database
it belongs to.
"""

from core.acquisition.toolkit_nhs.fetch import fetch_all as _fetch_all_nhs
from core.acquisition.toolkit_indicators.fetch import fetch_all as _fetch_all_indicators


def _fetchable_row_count(workfile_state, database: str) -> int:
    """Count of non-deleted, URL-bearing manifest rows for one database — matches the row filter each toolkit's own fetch_all applies internally."""
    return sum(
        1 for r in workfile_state.manifest_rows
        if str(r.get("deleted", "0")) != "1" and r.get("url", "").strip()
        and str(r.get("database", "nhs")).strip() == database
    )


def fetch_all(token: str, *, workfile_state, on_progress=None) -> list[dict]:
    """
    Full refresh of every chart in the manifest table, routed per row by its
    database column — "nhs" rows via toolkit_nhs, "indicators" rows via
    toolkit_indicators. Reports progress as one continuous total across
    both. Returns the combined result list, same shape as either toolkit's
    own fetch_all.
    """
    nhs_total = _fetchable_row_count(workfile_state, "nhs")
    indicators_total = _fetchable_row_count(workfile_state, "indicators")
    total_all = nhs_total + indicators_total

    def _wrap(offset):
        if not on_progress:
            return None
        def _inner(current, total, label):
            on_progress(offset + current, total_all, label)
        return _inner

    results = []
    results.extend(_fetch_all_nhs(token, workfile_state=workfile_state, on_progress=_wrap(0)))
    results.extend(_fetch_all_indicators(token, workfile_state=workfile_state, on_progress=_wrap(nhs_total)))
    return results
