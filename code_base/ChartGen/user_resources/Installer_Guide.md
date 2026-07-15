# ChartGen - Installer Guide

TBN Internal. Sits in user_resources alongside PPT_Template_Creation.md. Covers the installer, the update mechanism, and the versioning behind both. This is guidance and process, not one of the six governed reference documents, though the underlying behaviour it describes is documented there too (Functional Spec Section 5.1, Feature List, Glossary).

## What this covers

- Two independent version identifiers: software id and file version id
- The Inno Setup installer script and what it does
- Compiling and releasing a new version
- The Check for Update mechanism
- Installing and uninstalling on a colleague's machine

## Two version identifiers

ChartGen tracks the software id (this installed build) and the file version id (a `.cgw` workfile's internal structure) separately. They change independently. A software update with no `.cgw` structure change needs no file version bump. A `.cgw` structure change needs a file version bump regardless of the software id.

Both live in one place: `core/shared/infrastructure/version_compatibility.csv`.

| Key | Meaning |
|---|---|
| `software_id` | This build's own version, e.g. `0.0.1` |
| `file_version_written` | The file version id this build stamps into new/saved workfiles |
| `file_versions_readable` | Semicolon-delimited list of file version ids this build can still open |

At Open, a workfile whose file version id is not in `file_versions_readable` is a hard refuse. No partial read, no migration. See Functional Spec Section 5.1 for the full behaviour.

## The installer

`installer/ChartGen.iss` is an Inno Setup script, plain text, versioned in Git. It is the recipe. The compiled `.exe` is the dish, cooked fresh only when releasing, and is never itself committed to Git.

What it does:

- Installs to `%LOCALAPPDATA%\ChartGen`, no admin rights required
- Fixed AppId, so re-running the installer is recognised as an upgrade rather than a new install, and overwrites in place
- Bundles `app.py`, `run_chartgen.bat`, `requirements.txt`, the full `core` tree, `user_resources`, and `.streamlit`, excluding `__pycache__`
- Creates a desktop shortcut and a Start Menu shortcut, both using `installer/icons/ChartGen_app.ico`
- Registers the `.cgw` file association under HKCU, using `installer/icons/ChartGen_cgw.ico`, wired to open via `run_chartgen.bat "%1"`
- Deletes the `venv` folder on uninstall, since it is created on first run outside the installer's own file list

Double-click-open is optional, the same way opening Word or Excel without a file is normal. With no file argument, ChartGen starts exactly as it does today. With one, it is routed through the same Open Workfile flow as a manual open: same file version compatibility check, same concurrency decision step, nothing bypassed for this route.

## Releasing a new version

Day-to-day development does not touch the installer at all. Keep using `run_chartgen.bat` against the raw folder. The installer is only compiled when actually releasing.

1. Decide whether this release changes the `.cgw` internal structure. If so, bump `file_version_written` in `version_compatibility.csv` and add the new id to `file_versions_readable`. If not, leave both alone.
2. Bump `software_id` in `version_compatibility.csv`.
3. Update `MyAppVersion` and `MyAppVersionInfo` in `installer/ChartGen.iss` to match `software_id`. Use four-part numeric form for `MyAppVersionInfo` (e.g. `0.0.1` becomes `0.0.1.0`), since that is what Windows stores in the compiled `.exe`'s own file properties and what the update check reads.
4. Never change `AppId`. It is fixed forever. Changing it breaks upgrade detection for every colleague already running ChartGen.
5. Open `ChartGen.iss` in the Inno Setup Compiler and compile. Output lands in `installer/Output/ChartGen_Setup.exe`.
6. Test the installer locally before releasing it.
7. Copy `ChartGen_Setup.exe` to the SharePoint release location, replacing the previous copy:

`INTRANET\Resource Library\Tools & Templates\Internal Tools\ChartGen\ChartGen_Setup.exe`, under the OneDrive-for-Business synced root.

Steps 1 to 4 are the only points where forgetting matters. Nothing in the codebase catches a missed version bump automatically.

## Check for Update

A "Check for update" button sits in the sidebar, available only when no workfile is open. There is no automatic check on launch and no background polling. Checking is a deliberate user action, kept simple on purpose: no startup latency, no silent-failure handling to design for.

On click, ChartGen resolves the colleague's local OneDrive-for-Business sync root (via the `OneDriveCommercial` environment variable, with a folder-scan fallback), reads the release installer's version straight from its own PE file version resource, and compares it against the local `software_id`. Three outcomes: an error (path or file not resolvable), up to date, or an update available.

On confirming an available update, ChartGen copies the installer to a temporary folder, launches it, and exits its own process immediately, so the installer is not blocked by files ChartGen is still holding open. The installer then overwrites the install in place. The colleague relaunches ChartGen normally afterwards.

## Installing and uninstalling

To install: run `ChartGen_Setup.exe`. No admin prompt should appear. A desktop shortcut and Start Menu entry are created.

To uninstall or reinstall cleanly: Settings, Apps, ChartGen, Uninstall. This reverts the `.cgw` file association and icon, and removes the installed files and the `venv` folder. Re-running the installer afterwards is a clean install, not an upgrade over leftover state.

To upgrade in place: just run the newer `ChartGen_Setup.exe`. The fixed AppId means this overwrites the existing install rather than creating a second one.
