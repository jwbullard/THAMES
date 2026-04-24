; THAMES Windows installer script
; Builds with Inno Setup 6+ : https://jrsoftware.org/isdl.php
;
; Usage from a PowerShell or bash prompt at the repo root, AFTER running
; `pyinstaller thames-windows.spec --noconfirm` so dist\THAMES\ exists.
;
; Inno Setup 6 may be installed either machine-wide or per-user; the most
; common locations on this machine are:
;
;   "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"  installer\thames-windows.iss
;
; Output: dist\THAMES-1.0.0-alpha.2-setup.exe
;
; Design notes:
; - Installs to %LOCALAPPDATA%\Programs\THAMES\ (single-user, no admin / UAC).
; - User data lives in a SEPARATE tree at %LOCALAPPDATA%\THAMES\ (operations/,
;   database/, aggregate/, particle_shape_set/, ...). The uninstaller MUST NOT
;   touch that tree — testers' simulations and cached data must survive
;   uninstall + reinstall cycles.
; - Not code-signed for alpha. SmartScreen will flag the installer; that's
;   expected and documented in the alpha tester README.

#define MyAppName "THAMES"
#define MyAppVersion "1.0.0-alpha.2"
#define MyAppVersionDisplay "1.0.0 (alpha 2)"
#define MyAppPublisher "Texas A&M University"
#define MyAppURL "https://github.com/jwbullard/THAMES"
#define MyAppExeName "THAMES.exe"
#define MyBundleDir "..\dist\THAMES"

[Setup]
AppId={{8B4F1F8E-2C8A-4F4E-9C5A-THAMES000002}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersionDisplay}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion=1.0.0.2
; --- User-local install: no admin, no UAC ---
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
; --- Output artifact ---
OutputDir=..\dist
OutputBaseFilename=THAMES-{#MyAppVersion}-setup
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
; --- Branding ---
SetupIconFile=..\src\app\resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersionDisplay}
; --- Pre-release messaging ---
AppComments=Alpha pre-release. Not for production use.
ShowLanguageDialog=no
LicenseFile=..\LICENSE.md

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; The whole PyInstaller bundle. Inno Setup walks the tree recursively.
Source: "{#MyBundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autoprograms}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the program directory but DO NOT touch user data at
; %LOCALAPPDATA%\THAMES\ (operations, database, aggregate cache, etc.).
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  // Friendly heads-up that user data persists across upgrade/uninstall.
  // Only shown the first time on this machine (no marker check; the message
  // is informational not blocking).
  Result := True;
end;
