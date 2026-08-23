"""
url_parser.py
Parses Indicators toolkit URLs into their component parts. The URL shape is
entirely different from the NHS side. Real examples:

  https://members.nhsbenchmarking.nhs.uk/project/42/toolkit?a=6657&b=6658&reportId=420995&date=1353
  https://members.nhsbenchmarking.nhs.uk/project/42/toolkit?a=4646&date1353&reportId=420702&b=4647&c=4651&d=4652

project_id comes from the path (/project/{id}/toolkit), not a query param.
tier_id is a drill-down breadcrumb across up to five query params (a, b, c,
d, o). Only the deepest one present identifies the report's tier; the others
are shallower ancestors in the same hierarchy.

reportId is used directly. date is the period id the URL was generated
against. Some real URLs are missing its "=" ("date1353" rather than
"date=1353"); that is treated as "not present", not as malformed input.
"""

import re
from urllib.parse import urlparse

_PROJECT_ID_RE = re.compile(r"^/project/(\d+)/toolkit$")

# Deepest drill-down parameter present wins. "o" is deepest, "b" the
# shallowest fallback.
_TIER_PARAM_PRIORITY = ["o", "d", "c", "b"]


def _extract_int(url: str, key: str):
    """Return the integer following '{key}=' in url, or None if not present."""
    m = re.search(rf"[?&]{key}=(\d+)", url)
    return int(m.group(1)) if m else None


def parse_url(url: str) -> dict:
    """
    Parse a single Indicators toolkit URL into its components.
    Returns {"url", "project_id", "tier_id", "report_id", "date_id"}.
    date_id is None if the URL has no well-formed "date=" parameter.
    Raises ValueError if project_id or report_id can't be found — both are
    required for every subsequent API call.
    """
    parsed = urlparse(url)

    path = parsed.path.rstrip("/")
    m = _PROJECT_ID_RE.match(path)
    if not m:
        raise ValueError(f"Could not find /project/{{id}}/toolkit in URL path: {url}")
    project_id = int(m.group(1))

    tier_id = None
    for key in _TIER_PARAM_PRIORITY:
        tier_id = _extract_int(url, key)
        if tier_id is not None:
            break

    report_id = _extract_int(url, "reportId")
    if report_id is None:
        raise ValueError(f"Could not find reportId in URL: {url}")

    date_id = _extract_int(url, "date")

    return {
        "url": url,
        "project_id": project_id,
        "tier_id": tier_id,
        "report_id": report_id,
        "date_id": date_id,
    }
