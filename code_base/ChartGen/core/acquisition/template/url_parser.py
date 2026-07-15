"""
url_parser.py
Parses toolkit URLs into their component parts.
Each URL yields: project_id, tier_id, group, and option.
"""

from urllib.parse import urlparse, parse_qs


def parse_url(url: str) -> dict:
    """
    Parse a single toolkit URL into its components.
    Returns {"url", "project_id", "tier_id", "group", "option"}.
    """
    parsed = urlparse(url)

    # project_id is the final segment of the path e.g. /outputs/6 -> 6
    path_parts = parsed.path.rstrip("/").split("/")
    project_id = int(path_parts[-1])

    # Query parameters
    params = parse_qs(parsed.query)
    tier_id = int(params.get("tier", [0])[0])
    group = int(params.get("group", [0])[0])
    option = int(params.get("option", [0])[0])

    return {
        "url": url,
        "project_id": project_id,
        "tier_id": tier_id,
        "group": group,
        "option": option,
    }
