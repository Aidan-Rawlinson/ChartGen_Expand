"""
api_client.py
API calls to the NHS Benchmarking Indicators (ICS) toolkit API. Token
issuing is shared with the NHS submissions API (confirmed: one credential
set/token authorises both) — get_token is not duplicated here, callers
reuse core.acquisition.toolkit_nhs.api_client.get_token directly.

Deliberately NOT implemented: the tiers/tier/{tier_id} endpoint (VBA's
GetInfo). The VBA calls it and extracts a TierName from the response, but
never uses that value anywhere else — report title comes from
reportDetails instead. No data this pipeline stores depends on it.
"""

import requests

BASE_URL = "https://icsapi.nhsbenchmarking.nhs.uk"


def get_report_details(report_id, token: str) -> dict:
    """Retrieve report metadata — title (reportName) and formatting hint (formatModifier)."""
    response = requests.get(
        f"{BASE_URL}/reports/{report_id}/reportDetails",
        headers={"Accept": "application/json", "Token": token},
    )
    response.raise_for_status()
    return response.json()["data"]


def get_report_data(report_id, token: str) -> dict:
    """
    Retrieve the full per-period, per-organisation dataset for a report:
    availableDates, each with organisationList -> submissionData
    (submissionId, anonSubmissionCode, result). Also carries dateAverages /
    dateMedians / calculatedNationalAverages, which this pipeline discards —
    see transformers.py.
    """
    response = requests.get(
        f"{BASE_URL}/reports/{report_id}/reportDataDatesSpecificOptions",
        headers={"Accept": "application/json", "Token": token},
    )
    response.raise_for_status()
    return response.json()["data"]


def get_project_submissions_data(project_id, token: str) -> dict:
    """
    Retrieve the full /projects/{id}/submissions response for one project —
    not just its date list. Returns the raw data dict with (at least):

    - projectDates: each with an outputAvailability timestamp — a period is
      only visible once that timestamp has passed.
    - userOrganisations: every organisation this project exposes, each
      carrying organisationId (the ics-side id used throughout this
      toolkit) alongside externalOrganisationId (the matching
      nhs_organisations unit_id) — a live, per-project, always-current
      version of the mapping a static CSV extract used to stand in for
      (see Architecture Decision 10 and population_tables.py). Each
      organisation's submissionList also carries the real submissionName
      per submissionId, not just anonSubmissionCode.

    One call serves both purposes (dates, and org/submission identity) —
    callers extract whichever keys they need rather than this module
    duplicating the request per purpose.

    Note: the source VBA (GetVisibleDates) hardcodes project 42 regardless
    of the project_id argument it's given — confirmed as a VBA bug, not
    replicated here. This calls the actual project_id parsed from the
    chart's own URL, consistent with table_naming.py's own project_id-based
    naming (not hardcoded to one project either).
    """
    response = requests.get(
        f"{BASE_URL}/projects/{project_id}/submissions",
        headers={"Accept": "application/json", "Token": token},
    )
    response.raise_for_status()
    return response.json()["data"]
