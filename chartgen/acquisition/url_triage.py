"""
url_triage.py
Decides which toolkit database a chart URL belongs to ("nhs" or
"indicators"), from the URL's path shape alone, before either toolkit's own
url_parser runs. Called at manifest-row creation, from import_flow.py and
manifest_table/xlsx_reader.py.

Examples:
  NHS:         https://members.nhsbenchmarking.nhs.uk/outputs/6?tier=12&group=1&option=3
  Indicators:  https://members.nhsbenchmarking.nhs.uk/project/42/toolkit?a=6657&b=6658&reportId=420995&date=1353

Same front-end domain for both — the path shape is the only reliable signal.
"""

import re
from urllib.parse import urlparse

_INDICATORS_PATH_RE = re.compile(r"^/project/\d+/toolkit$")


def url_to_database(url: str) -> str:
    """
    Classify a toolkit URL as "nhs" or "indicators" by path shape. Defaults
    to "nhs" for anything that doesn't match the Indicators path pattern —
    today's only other database, and the pre-existing default — rather than
    raising, so a malformed or unrecognised URL still gets a manifest row.
    """
    path = urlparse(url).path.rstrip("/")
    if _INDICATORS_PATH_RE.match(path):
        return "indicators"
    return "nhs"
