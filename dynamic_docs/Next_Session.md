<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

The installer and update feature is built, compiled, and tested end to end. Nothing urgent is broken. Good next steps, roughly in order of usefulness:

1. **Test the "update available" path for real.** Everything tested so far is either "up to date" or a graceful failure against the placeholder file. To actually exercise the update-available branch: bump `software_id` in `version_compatibility.csv` locally (without recompiling the installer), run Check for Update, confirm it reports an update is available, and walk through the download-and-relaunch flow. Revert the local bump afterwards.
2. **Decide the real first release version.** `0.0.1` was a placeholder to get the mechanism working. Worth deciding what the actual first alpha release should be called before this goes to any colleague.
3. **Consider Uninstall Delete scope.** Currently only `venv` is explicitly cleaned up on uninstall beyond what Inno Setup tracks itself. Worth a second pass once more runtime-generated folders exist (e.g. anything under `outputs/` if that ever ends up inside the install folder rather than beside a workfile - it shouldn't, per Architecture, but worth a conscious check).
4. **Multiple database support and manual data entry** remain the two clearest gaps in Part 1/3 of the Feature List if project work resumes on core features rather than the installer.

## Open questions for the user

- Is `%LOCALAPPDATA%` still the right install location long-term, or does this need revisiting once more colleagues are involved (e.g. shared-machine scenarios)?
- Should the release checklist's manual version-bump step ever get a safety net (e.g. a small script that checks `version_compatibility.csv` and `ChartGen.iss` agree before compiling), or is manual discipline sufficient given release cadence is expected to be low?

## Not urgent, just noted

- `Installer_Guide.md` is user-resources guidance, not one of the six governed documents. If it drifts from actual behaviour after further changes, it won't be caught by the six-document ground-truth discipline - worth an occasional manual check.
