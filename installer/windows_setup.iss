; ──────────────────────────────────────────────────────────────────────────────
; AMAZON AI - Windows Installer (Inno Setup)
; ──────────────────────────────────────────────────────────────────────────────
; Download Inno Setup: https://jrsoftware.org/isdl.php
; Open this file in Inno Setup Compiler → Click "Build" → Get AMAZON_AI_Setup.exe
; ──────────────────────────────────────────────────────────────────────────────

#define MyAppName     "AMAZON AI"
#define MyAppVersion  "1.0.0"
#define MyAppPublisher "AMAZON AI"
#define MyAppURL      "https://github.com/your-repo/amazon-ai"
#define MyAppExeName  "AMAZON AI.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install location
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Installer appearance
WizardStyle=modern
SetupIconFile=..\assets\nova_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression (best for large apps)
Compression=lzma2/ultra64
SolidCompression=yes

; Privilege
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Output
OutputDir=..\dist
OutputBaseFilename=AMAZON_AI_Setup
OutputManifestFile=AMAZON_AI_Setup_Manifest.txt

; Size (approximate - adjust after build)
; The actual size depends on PyInstaller output
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Copy the entire PyInstaller dist output
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Include assets separately in case they're not bundled
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs

; Include ML model files
Source: "..\ml\label_map.json"; DestDir: "{app}\ml"; Flags: ignoreversion
Source: "..\ml\nlu_model\*"; DestDir: "{app}\ml\nlu_model"; Flags: ignoreversion recursesubdirs
Source: "..\ml\semantic_index\*"; DestDir: "{app}\ml\semantic_index"; Flags: ignoreversion recursesubdirs

; Database & cache
Source: "..\database\*"; DestDir: "{app}\database"; Flags: ignoreversion recursesubdirs
Source: "..\cache\*"; DestDir: "{app}\cache"; Flags: ignoreversion recursesubdirs
Source: "..\learning\*"; DestDir: "{app}\learning"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\database"
Type: filesandordirs; Name: "{app}\learning"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\temp"
