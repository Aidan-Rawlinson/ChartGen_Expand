; ChartGen.iss
; Inno Setup script for ChartGen.
;
; AppId is FIXED forever - never change it across releases. It is how
; Windows recognises "same application, newer version" on re-run, which is
; what makes upgrades overwrite in place rather than creating a duplicate
; install (Decisions.md, installer plan).
;
; This is a plain-text recipe, versioned in Git alongside the code. The
; compiled .exe it produces is the release artifact - never itself stored
; in Git, copied instead to the SharePoint release location for the
; Check for Update flow to find.
;
; To compile: open this file in the Inno Setup Compiler (or run ISCC.exe
; against it) from a machine with Inno Setup installed. Requires the two
; icon files below to already be sitting in installer\icons\ alongside
; this script - see Installer_Guide.md for exactly what to place where.

#define MyAppName "ChartGen"
#define MyAppVersion "0.0.3"
#define MyAppVersionInfo "0.0.3.0"

[Setup]
AppId={{A9AF1BB5-9E70-4EA1-BCFC-5AB2C1613B48}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersionInfo}
DefaultDirName={localappdata}\ChartGen
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=ChartGen_Setup
OutputDir=Output
Compression=lzma
SolidCompression=yes
SetupIconFile=icons\ChartGen_app.ico
UninstallDisplayIcon={app}\icons\ChartGen_app.ico
UninstallDisplayName={#MyAppName}

; PrivilegesRequired=lowest + HKCU-only registry entries below keep this a
; no-admin-rights install, consistent with the %LOCALAPPDATA% location -
; deliberate given no installer/no admin access was assumed for this phase.

[Files]
; Top-level application files
Source: "..\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\run_chartgen.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Full core/ package tree and user_resources/ - "grab everything under this
; folder" per the maintenance discussion, so ordinary code changes inside
; existing files/folders need no edits here. __pycache__/.pyc excluded -
; stale bytecode, not source, regenerated fresh on first run anyway.
Source: "..\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__;*.pyc"
Source: "..\user_resources\*"; DestDir: "{app}\user_resources"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\.streamlit\*"; DestDir: "{app}\.streamlit"; Flags: ignoreversion recursesubdirs createallsubdirs

; Icons - bundled into the install so shortcuts/associations keep working
; after the original installer .exe is gone.
Source: "icons\ChartGen_app.ico"; DestDir: "{app}\icons"; Flags: ignoreversion
Source: "icons\ChartGen_cgw.ico"; DestDir: "{app}\icons"; Flags: ignoreversion

[Icons]
; Desktop shortcut - same app icon as the taskbar/Explorer identity.
Name: "{userdesktop}\ChartGen"; Filename: "{app}\run_chartgen.bat"; \
    IconFilename: "{app}\icons\ChartGen_app.ico"; WorkingDir: "{app}"

; Start menu shortcut (DisableProgramGroupPage keeps this to a single
; entry rather than prompting for a folder name).
Name: "{autoprograms}\ChartGen"; Filename: "{app}\run_chartgen.bat"; \
    IconFilename: "{app}\icons\ChartGen_app.ico"; WorkingDir: "{app}"

[Registry]
; .cgw file association - HKCU (not HKLM) to match the no-admin,
; per-user install. uninsdeletevalue/uninsdeletekey mean a normal
; Uninstall cleanly reverts all of this, no manual registry edits needed
; to get back to a clean slate for retesting.
Root: HKCU; Subkey: "Software\Classes\.cgw"; ValueType: string; ValueName: ""; \
    ValueData: "ChartGen.Workfile"; Flags: uninsdeletevalue

Root: HKCU; Subkey: "Software\Classes\ChartGen.Workfile"; ValueType: string; ValueName: ""; \
    ValueData: "ChartGen Workfile"; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\Classes\ChartGen.Workfile\DefaultIcon"; ValueType: string; ValueName: ""; \
    ValueData: "{app}\icons\ChartGen_cgw.ico"

; Double-click open: launches run_chartgen.bat with the .cgw path as its
; first argument. run_chartgen.bat passes this through to Streamlit
; ("-- %*"), which app.py reads via core.session_shell.lifecycle.startup_file
; and routes into the normal Open Workfile flow - same lock-decision step,
; same file-version compatibility check, nothing bypassed for this route.
Root: HKCU; Subkey: "Software\Classes\ChartGen.Workfile\shell\open\command"; ValueType: string; ValueName: ""; \
    ValueData: """{app}\run_chartgen.bat"" ""%1"""

[UninstallDelete]
; venv is created on first run by run_chartgen.bat, outside [Files]'
; knowledge - remove it explicitly on uninstall so nothing's left behind.
Type: filesandordirs; Name: "{app}\venv"
