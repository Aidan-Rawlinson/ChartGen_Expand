"""
url_triage.py
Decides which toolkit database a chart URL belongs to ("nhs" or
"indicators"), from the URL's own shape alone — before either toolkit
package's own url_parser runs. Lives outside both toolkit_nhs/ and
toolkit_indicators/ because it has to be callable from manifest-row
creation (workfile_file.new_manifest_row's callers, import_flow.py and
xlsx_reader.py) without either toolkit package depending on the other, and
without workfile.state depending on acquisition (one-way dependency rule,
Architecture Section 2).

Real examples seen so far:
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
