"""
Tests for acquisition/url_triage.py

acquisition/CLAUDE.md: "A chart URL is classified 'nhs' or 'indicators' by
path shape alone, once, at manifest-row creation... Both share the same
front-end domain, so the path is the only reliable signal. From that point
on the manifest row's database column is the source of truth. Do not
re-derive it."

Getting this wrong sends a URL to the wrong toolkit's parser and the fetch
fails, so it is at least loud. The subtler risk is a change that starts
looking at the domain or the query string, which would work on today's URLs
and break on tomorrow's.

The deliberate design decision recorded here is the default: anything that
does not match the Indicators path becomes "nhs" rather than raising, "so a
malformed or unrecognised URL still gets a manifest row".
"""

from chartgen.acquisition.url_triage import url_to_database

NHS_URL = "https://members.nhsbenchmarking.nhs.uk/outputs/6?tier=12&group=1&option=3"
INDICATORS_URL = (
    "https://members.nhsbenchmarking.nhs.uk/project/42/toolkit"
    "?a=6657&b=6658&reportId=420995&date=1353"
)


# ---------------------------------------------------------------------------
# The two real path shapes
# ---------------------------------------------------------------------------

def test_an_outputs_path_is_the_nhs_toolkit():
    assert url_to_database(NHS_URL) == "nhs"


def test_a_project_toolkit_path_is_the_indicators_toolkit():
    assert url_to_database(INDICATORS_URL) == "indicators"


def test_the_two_are_told_apart_despite_sharing_a_domain():
    """
    The reason path shape is used at all. If classification ever started
    from the host, both would land in the same bucket.
    """
    assert url_to_database(NHS_URL) != url_to_database(INDICATORS_URL)


# ---------------------------------------------------------------------------
# The query string plays no part
# ---------------------------------------------------------------------------

def test_the_query_string_is_ignored():
    bare = "https://members.nhsbenchmarking.nhs.uk/project/42/toolkit"
    assert url_to_database(bare) == "indicators"


def test_a_trailing_slash_does_not_change_the_answer():
    assert url_to_database("https://members.nhsbenchmarking.nhs.uk/project/42/toolkit/") == "indicators"


def test_any_project_number_is_recognised():
    for project_id in ["1", "42", "12345"]:
        url = f"https://members.nhsbenchmarking.nhs.uk/project/{project_id}/toolkit"
        assert url_to_database(url) == "indicators"


# ---------------------------------------------------------------------------
# The documented default
# ---------------------------------------------------------------------------

def test_an_unrecognised_url_defaults_to_nhs_rather_than_raising():
    """
    Deliberate: a malformed URL still gets a manifest row, so the user sees
    it in the table and can correct it, rather than the import failing.
    """
    assert url_to_database("https://example.com/something/else") == "nhs"


def test_an_empty_url_defaults_to_nhs_rather_than_raising():
    assert url_to_database("") == "nhs"


def test_a_project_path_without_the_toolkit_segment_is_not_indicators():
    """
    The pattern is anchored to the whole path for a reason: a project page
    that is not the toolkit view is not an Indicators chart URL.
    """
    assert url_to_database("https://members.nhsbenchmarking.nhs.uk/project/42") == "nhs"


def test_a_deeper_path_below_toolkit_is_not_indicators():
    assert url_to_database("https://members.nhsbenchmarking.nhs.uk/project/42/toolkit/extra") == "nhs"
