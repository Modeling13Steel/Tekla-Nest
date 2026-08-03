; Inno Setup Script for Tekla Nest Optimizer
; Download Inno Setup: https://jrsoftware.org/isinfo.php
;
; Build steps:
;   1. Run:  make binary-dir     (creates dist/tekla-nest/ folder)
;   2. Run:  iscc installer.iss  (creates dist/tekla-nest-setup.exe)

#define MyAppName "Tekla Nest Optimizer"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "CTW / BMW Group"
#define MyAppExeName "tekla-nest.exe"

[Setup]
AppId={{B4F2E3A1-7C5D-4E8F-9A2B-1D3C5E7F9A0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=tekla-nest-setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=resources\logo_cut_bar_mark.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application (onedir bundle)
Source: "dist\tekla-nest\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Bundled Python with pythonnet (for Tekla integration)
; Built by: scripts/prepare-python-embed.ps1
Source: "build\python-embed\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; VC++ Redistributable (download vc_redist.x64.exe from Microsoft and place in resources/)
; https://aka.ms/vs/17/release/vc_redist.x64.exe
Source: "resources\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VCRedistNeedsInstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Install VC++ Redistributable silently if needed
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; \
    StatusMsg: "Installing Visual C++ Runtime..."; Flags: waituntilterminated; \
    Check: VCRedistNeedsInstall

; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[Code]
function VCRedistNeedsInstall: Boolean;
var
  Version: String;
begin
  // Check if VC++ 2015-2022 redistributable is already installed
  Result := True;
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
     'Version', Version) then
  begin
    // v14.x is installed — check minimum version
    Result := (CompareStr(Version, 'v14.30') < 0);
  end;
end;
