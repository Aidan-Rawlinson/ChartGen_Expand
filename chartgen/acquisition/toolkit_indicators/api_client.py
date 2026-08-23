"""
api_client.py
API calls to the NHS Benchmarking Indicators (ICS) toolkit API.

One credential set and token authorises both this API and the NHS
submissions API, so get_token is not duplicated here. Callers reuse
toolkit_nhs.api_client.get_token directly.
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
      carrying organisationId (the ics-side id) alongside
      externalOrganisationId (the matching nhs_organisations unit_id).
      This is the live organisation-id mapping, resolved per project on
      every call. Each organisation's submissionList also carries the real
      submissionName per submissionId, not just anonSubmissionCode.

    One call serves both purposes. Callers extract whichever keys they
    need.
    """
    response = requests.get(
        f"{BASE_URL}/projects/{project_id}/submissions",
        headers={"Accept": "application/json", "Token": token},
    )
    response.raise_for_status()
    return response.json()["data"]
