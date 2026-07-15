"""
update_check.py
"Check for Update" logic: resolves the SharePoint-via-OneDrive release
location, reads the release installer's own version (PE file version
resource - no separate version-marker file), and compares it against this
build's software id. Check only - downloading and launching the installer
is the caller's job (update_form.py), gated behind explicit confirmation.

The OneDrive-synced local path is resolved fresh on every call, never
stored - consistent with how ChartGen already treats OneDrive-synced paths
elsewhere (workfiles themselves are opened from arbitrary synced paths too).
"""

import os

from core.shared.infrastructure.version_compatibility import get_software_id

try:
    import win32api
except ImportError:
    win32api = None  # allows this module to import on a machine without pywin32

# Fixed tail path within the resolved OneDrive root - the same for every
# colleague once the shared library is synced; only the root differs per user.
RELEASE_TAIL_PATH = os.path.join(
    "INTRANET", "Resource Library", "Tools & Templates",
    "Internal Tools", "ChartGen", "ChartGen_Setup.exe",
)


def resolve_onedrive_root() -> str:
    """
    Resolve this machine's local, per-user path to the synced OneDrive-for-
    Business root (e.g. C:\\Users\\{user}\\OneDrive - RCIGroup), without
    storing or asking for it. OneDrive sets this as an environment variable
    once the account is signed in and syncing.
    """
    root = os.environ.get("OneDriveCommercial", "").strip()
    if root and os.path.isdir(root):
        return root

    # Fallback for machines where OneDriveCommercial isn't set (e.g. multiple
    # business accounts synced): scan the user's home folder for an
    # "OneDrive - *" folder.
    home = os.path.expanduser("~")
    try:
        for name in os.listdir(home):
            if name.startswith("OneDrive - "):
                candidate = os.path.join(home, name)
                if os.path.isdir(candidate):
                    return candidate
    except OSError:
        pass
    return ""


def get_release_installer_path() -> str:
    """Full local path to the release installer, resolved fresh each call."""
    root = resolve_onedrive_root()
    if not root:
        return ""
    return os.path.join(root, RELEASE_TAIL_PATH)


def get_release_version() -> str:
    """
    Read the release installer's version straight from its PE file version
    resource. Returns "" if the file is missing, unreadable, not a valid
    Windows executable, or pywin32 isn't available.
    """
    path = get_release_installer_path()
    if not path or not os.path.exists(path) or win32api is None:
        return ""
    try:
        info = win32api.GetFileVersionInfo(path, "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return "%d.%d.%d.%d" % (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return ""


def get_local_version() -> str:
    """This build's own software id - the local side of the comparison."""
    return get_software_id()


def _normalise_version(v: str):
    """
    Parse a version string into a fixed-length numeric tuple for comparison,
    padding short forms with zeros - e.g. "0.0.1" and "0.0.1.0" both become
    (0, 0, 1, 0). Returns None if any part isn't a plain integer, in which
    case callers fall back to exact string comparison.
    """
    parts = v.split(".")
    if len(parts) > 4 or not all(p.isdigit() for p in parts):
        return None
    parts = parts + ["0"] * (4 - len(parts))
    return tuple(int(p) for p in parts)


def _versions_equal(a: str, b: str) -> bool:
    na, nb = _normalise_version(a), _normalise_version(b)
    if na is not None and nb is not None:
        return na == nb
    return a == b


def check_for_update() -> dict:
    """
    Runs the comparison and returns a dict describing the outcome for the
    UI to render. Never downloads or applies anything itself.

    Possible "status" values: "error", "up_to_date", "update_available".
    """
    local = get_local_version()
    release_path = get_release_installer_path()

    if not release_path:
        return {
            "status": "error",
            "message": (
                "Could not find your OneDrive-synced ChartGen release folder. "
                "Check OneDrive is signed in and the shared library is synced."
            ),
        }

    if not os.path.exists(release_path):
        return {
            "status": "error",
            "message": f"Resolved the release folder, but no installer was found there yet "
                       f"({os.path.basename(release_path)}).",
        }

    release_version = get_release_version()
    if not release_version:
        return {
            "status": "error",
            "message": (
                f"Found {os.path.basename(release_path)}, but couldn't read a version from it. "
                "It may still be syncing, or isn't a valid installer."
            ),
        }

    if _versions_equal(release_version, local):
        return {"status": "up_to_date", "local_version": local}

    return {
        "status": "update_available",
        "local_version": local,
        "release_version": release_version,
        "installer_path": release_path,
    }
