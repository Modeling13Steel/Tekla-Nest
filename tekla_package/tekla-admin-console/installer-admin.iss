; Inno Setup Script for Tekla Nest Admin
; Build steps:
;   1. Run:  make binary-admin-dir
;   2. Run:  iscc installer-admin.iss

#define MyAppName "Tekla Nest Admin"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "CTW / BMW Group"
#define MyAppExeName "tekla-nest-admin.exe"

[Setup]
AppId={{7B0A02A7-47B5-44E6-8D30-4C02B86B26C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=tekla-nest-admin-setup
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
; Admin application only. Do not include the customer app bundle or license-server infrastructure.
Source: "dist\tekla-nest-admin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; VC++ Redistributable (download vc_redist.x64.exe from Microsoft and place in resources/)
Source: "resources\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VCRedistNeedsInstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; \
    StatusMsg: "Installing Visual C++ Runtime..."; Flags: waituntilterminated; \
    Check: VCRedistNeedsInstall

Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[Code]
function VCRedistNeedsInstall: Boolean;
var
  Version: String;
begin
  Result := True;
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
     'Version', Version) then
  begin
    Result := (CompareStr(Version, 'v14.30') < 0);
  end;
end;
