"""
login.py
Credential validation, token handling, and last-used-username persistence —
mechanics only. Widgets and the sign-in form live in core/ui/login_form.py.
Split out of the old streamlit_frontend/login.py (mechanics fused with
widgets) and local_config.py (username persistence misfiled as shared infra).
"""

import os
import csv

from core.acquisition.toolkit_nhs.api_client import get_token

_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.csv")


def load_last_username() -> str:
    """Return the last successfully authenticated username, or empty string."""
    if not os.path.exists(_CREDENTIALS_PATH):
        return ""
    with open(_CREDENTIALS_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        row = next(reader, None)
        if row is None:
            return ""
        return row.get("username", "").strip()


def save_last_username(username: str):
    """Persist the username only — no password stored."""
    with open(_CREDENTIALS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["username"])
        writer.writeheader()
        writer.writerow({"username": username})


def authenticate(email: str, password: str) -> str:
    """Validate credentials against the API, save the username, and return a session token."""
    token = get_token(email.strip(), password)
    save_last_username(email.strip())
    return token
