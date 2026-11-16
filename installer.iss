; Inno Setup Script for Tekla Nest Optimizer
; Download Inno Setup: https://jrsoftware.org/isinfo.php
;
; Build steps:
;   1. Run:  make binary-dir     (creates dist/tekla-nest/ folder)
;   2. Run:  make installer      (passes /DMyAppVersion to iscc; creates dist/tekla-nest-setup.exe)

#define MyAppName "Tekla Nest Optimizer"
; Version comes from pyproject.toml only: CI / `make installer` pass
;   iscc /DMyAppVersion=<version> <this file>
#ifndef MyAppVersion
  #error MyAppVersion is not defined. Build with: iscc /DMyAppVersion=<version from pyproject.toml>
#endif
#define MyAppPublisher "CTW / BMW Group"
#define MyAppExeName "tekla-nest.exe"

[Setup]
AppId={{B4F2E3A1-7C5D-4E8F-9A2B-1D3C5E7F9A0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
; Must match src/tekla_nest/single_instance.py (the app creates this mutex).
AppMutex=TeklaNestOptimizer.SingleInstance
; Restart Manager: offer to close running app files (e.g. bundled python.exe).
CloseApplications=yes
RestartApplications=no
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

[CustomMessages]
english.DowngradeBlocked=A newer version (%1) of {#MyAppName} is already installed. This setup contains version %2.%n%nUninstall the newer version first, or run this setup with /VERYSILENT /ALLOWDOWNGRADE.
portuguese.DowngradeBlocked=Já está instalada uma versão mais recente (%1) do {#MyAppName}. Este instalador contém a versão %2.%n%nDesinstale primeiro a versão mais recente, ou execute este instalador com /VERYSILENT /ALLOWDOWNGRADE.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Drop the previous PyInstaller bundle so renamed/removed .pyd/.dll files from
; an older build cannot shadow the new ones. User data (license token in
; %USERPROFILE%\.teklanest, preferences in %USERPROFILE%\.tekla_nest) is not under {app}.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\python"

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

const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{B4F2E3A1-7C5D-4E8F-9A2B-1D3C5E7F9A0B}_is1';

// DisplayVersion of an existing install ('' if none). HKLM is the 64-bit
// view in 64-bit install mode; HKLM32 / HKCU cover older or per-user installs.
function GetInstalledVersion(): String;
begin
  Result := '';
  if not RegQueryStringValue(HKLM, UninstallKey, 'DisplayVersion', Result) then
    if not RegQueryStringValue(HKLM32, UninstallKey, 'DisplayVersion', Result) then
      if not RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', Result) then
        Result := '';
end;

// Numeric dotted-version compare: <0 if A<B, 0 if equal, >0 if A>B.
// Missing or non-numeric parts count as 0 ('2.1' = '2.1.0', 'dev' = '0').
function CompareVersions(VersionA, VersionB: String): Integer;
var
  A, B: String;
  P, NA, NB: Integer;
begin
  A := VersionA;
  B := VersionB;
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    P := Pos('.', A);
    if P > 0 then
    begin
      NA := StrToIntDef(Copy(A, 1, P - 1), 0);
      Delete(A, 1, P);
    end
    else
    begin
      NA := StrToIntDef(A, 0);
      A := '';
    end;
    P := Pos('.', B);
    if P > 0 then
    begin
      NB := StrToIntDef(Copy(B, 1, P - 1), 0);
      Delete(B, 1, P);
    end
    else
    begin
      NB := StrToIntDef(B, 0);
      B := '';
    end;
    Result := NA - NB;
  end;
end;

function HasSwitch(const Name: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Name) = 0 then
      Result := True;
end;

// Same or older version installed: proceed (repair / upgrade in place).
// Newer installed: refuse, unless silent with /ALLOWDOWNGRADE.
function InitializeSetup(): Boolean;
var
  Installed: String;
begin
  Result := True;
  Installed := GetInstalledVersion();
  if (Installed <> '') and (CompareVersions(Installed, '{#MyAppVersion}') > 0) then
  begin
    if WizardSilent and HasSwitch('/ALLOWDOWNGRADE') then
      Log('Downgrade from ' + Installed + ' allowed by /ALLOWDOWNGRADE')
    else
    begin
      SuppressibleMsgBox(FmtMessage(CustomMessage('DowngradeBlocked'),
        [Installed, '{#MyAppVersion}']), mbCriticalError, MB_OK, IDOK);
      Result := False;
    end;
  end;
end;
