<!-- Purpose: A session-by-session history of what was built and what was decided. The project record. Authored by Claude at session level, not micro-decision level. -->

## Session: Installer, update mechanism, and versioning

Built the full installer and update feature end to end, from initial planning through to a real compiled installer tested on the user's machine.

Covered in order: confirmed the install-location decision (%LOCALAPPDATA%, no admin rights), built the file version compatibility mechanism (a new software id / file version id distinction, with a hard refuse at Open on incompatible file versions), built optional double-click-open (reusing the existing Open Workfile flow rather than a separate silent-open path), and built the Check for Update mechanism (manual button only, OneDrive-for-Business path resolution, PE metadata version comparison, no automatic or background checking).

Designed both icon assets collaboratively with the user through many iterative rounds (colour palette matched against a reference image the user supplied, chart-and-slider composition, ascending bar heights, dot placement), then rasterised them into real multi-resolution .ico files using PIL in the sandboxed environment (no SVG renderer was available, so shapes were redrawn programmatically rather than converted directly from the SVG source).

Wrote the Inno Setup script (installer/ChartGen.iss): fixed AppId, .cgw file association under HKCU, both icons, venv cleanup on uninstall. User installed Inno Setup 7 and compiled it successfully on the first attempt. User then tested the installer, confirmed the .cgw icon, confirmed double-click-open, and copied the real installer to the actual SharePoint release location (replacing the placeholder file that had been used for earlier path-resolution testing).

Updated project documentation: Functional Spec Section 5 restructured into 5.1 (File Version Compatibility, new) and 5.2 (Concurrency, existing content unchanged), per the user's explicit steer to keep this behaviour in one document rather than split between Architecture and Functional Spec. Added matching Glossary terms and a Feature List row, and corrected two Feature List rows that had gone stale (file association and custom icon, previously marked "Not built, requires an installer"). Wrote a new standalone user_resources/Installer_Guide.md covering the whole feature, the release checklist, and install/uninstall steps.

Consolidated a duplication found along the way: workfile_file.py had its own separate CHARTGEN_VERSION constant, now replaced with a reference to the single version_compatibility.csv source of truth.


## Session: Expansion planning and Step 1 — the manifest table

Opened by deleting the stale Architecture Decision 9 (application location) — obsolete now the installer exists and the situation is nuanced.

Planned the multi-project / multi-database expansion with the user: reviewed the intended shift (one .cgw no longer tied to one project/year; just-in-time credentials; URL triage by database; submissions vs organisations split), and agreed a seven-step development plan, now recorded in Current_State.md. Marked the project phase explicitly as Expansion in Current_State.md, with a standing instruction block for future Claude sessions.

Built Step 1 end to end — the manifest table:

- Designed the schema with the user: chart_ref (display index, renumbering), hex_id (stable 5-digit hex identity, names the cache file), url, chart_title, database, project/service/year, shape_type, source (Template / Direct Input), deleted flag, added/updated timestamps, `...` placeholders pre-fetch.
- Consolidated three overlapping stores into one: workfile_config/urls.csv and data_cache/manifest.json both deleted, replaced by data_cache/manifest.csv as single source of truth. Cache files renamed {hex_id}.json. File version and software id bumped to 0.0.2; 0.0.1 workfiles hard-refuse.
- Decoupled fetching from template processing: extraction populates the table and generates the Running Order immediately (cache_file assignable pre-fetch thanks to hex_id); the Imports tab's Fetch button is the single fetch, a full refresh updating each row's fetch-populated columns.
- New package core/acquisition/manifest_table/ for the Excel round-trip (formatted export with 300 blank input rows; import semantics: blank hex_id = new Direct Input row, missing hex_id = deleted with data retained, unknown hex_id rejected, template re-upload resurrects deleted URLs under their original identity).
- Reworked the Imports tab: read-only table display, Excel-only editing (an in-table editor was built, then removed at the user's request after live testing), upload behind a toggle button matching the Running Order tab's pattern.
- Verified with sandbox compile checks and functional tests of the merge/import semantics; user live-tested end to end including output generation. One mid-test failure (Running Order referencing old-style cache names) was diagnosed as a stale hot-reloaded process, resolved by relaunch and template re-process.

Dead-code sweep after the build: removed the unused label parameter from parse_url, removed the unused SYSTEM_COLUMNS constant, fixed a stale comment in generation.py.

Updated all four affected governed documents (Architecture, Functional Spec, Feature List, Glossary) per the agreed proposals; mirror copies written mid-session and re-uploaded to Project Files by the user at Close-down.
