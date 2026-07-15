<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

## Status: In progress - installer and update mechanism built and tested

This session built the full installer and update feature: file version compatibility, optional double-click-open, the Check for Update mechanism, the Inno Setup script, both icon assets, and the supporting documentation. All of it has been tested successfully on the user's machine, including a real compiled installer.

### What works

- File version compatibility: `core/shared/infrastructure/version_compatibility.csv` and `.py` hold the software id, the file version id this build writes, and the readable-versions list. `WorkfileState.file_version_id` is written on Save/New and checked on Open. An incompatible file version id is a hard refuse in `open_workfile_form.py`, before the lock-decision step.
- Optional double-click-open: `core/session_shell/lifecycle/startup_file.py` reads a `.cgw` path from the startup arguments and routes it through the existing Open Workfile flow, same compatibility check, same lock-decision step. `run_chartgen.bat` passes arguments through to Streamlit. Not required - launching with no file behaves as before.
- Check for Update: `core/session_shell/lifecycle/update_check.py` resolves the local OneDrive-for-Business sync root, reads the release installer's version from its own PE metadata, and compares against the local software id. `core/ui/workfile/update_form.py` is the sidebar-triggered modal, available only with no workfile open. Confirms, copies the installer to a temp folder, launches it, and exits ChartGen's own process.
- Installer: `installer/ChartGen.iss` is a working Inno Setup script, compiled successfully to `ChartGen_Setup.exe`. Installs to `%LOCALAPPDATA%\ChartGen`, no admin rights, fixed AppId, `.cgw` file association under HKCU with the custom icon, desktop and Start Menu shortcuts.
- Icons: `installer/icons/ChartGen_app.ico` and `ChartGen_cgw.ico`, both multi-resolution (16 to 256px), rounded-square and folded-corner document designs in a shared blue and amber palette.
- version_compatibility.csv currently holds software_id 0.0.1, file_version_written 0.0.1, file_versions_readable 0.0.1.
- Real end-to-end test completed: installer compiled, installed cleanly, `.cgw` icon confirmed, double-click-open confirmed, installer copied to the real SharePoint release location (`INTRANET\Resource Library\Tools & Templates\Internal Tools\ChartGen\ChartGen_Setup.exe` under the user's OneDrive-for-Business sync).

### Documentation

- `user_resources/Installer_Guide.md` written: covers the two version identifiers, the installer, the release checklist, Check for Update, and install/uninstall steps.
- Functional Spec Section 5 restructured into 5.1 (File Version Compatibility) and 5.2 (Concurrency).
- Glossary: added "File version id" and "Software id" under Cluster 4.
- Feature List: added a row for the file version compatibility check; corrected two stale "Not built" rows (file association, custom `.cgw` icon) to Complete.
- Architecture document deliberately left untouched for this feature, per the user's steer to keep the behaviour in one document rather than split.

### Known gaps / not yet done

- No real second version has been tested through the "update available" path yet - only "up to date" and graceful-failure (placeholder file) have been exercised.
- Version-bump discipline (Installer_Guide.md's release checklist) is manual; nothing in the codebase catches a missed bump.
