<!-- Purpose: A session-by-session history of what was built and what was decided. The project record. Authored by Claude at session level, not micro-decision level. -->

## Session: Installer, update mechanism, and versioning

Built the full installer and update feature end to end, from initial planning through to a real compiled installer tested on the user's machine.

Covered in order: confirmed the install-location decision (%LOCALAPPDATA%, no admin rights), built the file version compatibility mechanism (a new software id / file version id distinction, with a hard refuse at Open on incompatible file versions), built optional double-click-open (reusing the existing Open Workfile flow rather than a separate silent-open path), and built the Check for Update mechanism (manual button only, OneDrive-for-Business path resolution, PE metadata version comparison, no automatic or background checking).

Designed both icon assets collaboratively with the user through many iterative rounds (colour palette matched against a reference image the user supplied, chart-and-slider composition, ascending bar heights, dot placement), then rasterised them into real multi-resolution .ico files using PIL in the sandboxed environment (no SVG renderer was available, so shapes were redrawn programmatically rather than converted directly from the SVG source).

Wrote the Inno Setup script (installer/ChartGen.iss): fixed AppId, .cgw file association under HKCU, both icons, venv cleanup on uninstall. User installed Inno Setup 7 and compiled it successfully on the first attempt. User then tested the installer, confirmed the .cgw icon, confirmed double-click-open, and copied the real installer to the actual SharePoint release location (replacing the placeholder file that had been used for earlier path-resolution testing).

Updated project documentation: Functional Spec Section 5 restructured into 5.1 (File Version Compatibility, new) and 5.2 (Concurrency, existing content unchanged), per the user's explicit steer to keep this behaviour in one document rather than split between Architecture and Functional Spec. Added matching Glossary terms and a Feature List row, and corrected two Feature List rows that had gone stale (file association and custom icon, previously marked "Not built, requires an installer"). Wrote a new standalone user_resources/Installer_Guide.md covering the whole feature, the release checklist, and install/uninstall steps.

Consolidated a duplication found along the way: workfile_file.py had its own separate CHARTGEN_VERSION constant, now replaced with a reference to the single version_compatibility.csv source of truth.
