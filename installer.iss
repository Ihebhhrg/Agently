; Agently — Inno Setup script.
; Build two variants by passing /D defines:
;   ISCC /DSTAGEDIR=... /DOUTNAME=... /DVARIANT=... installer.iss
#ifndef STAGEDIR
  #define STAGEDIR "dist\Agently"
#endif
#ifndef OUTNAME
  #define OUTNAME "Agently-Setup-Lite"
#endif
#ifndef VARIANT
  #define VARIANT "Lite"
#endif

[Setup]
AppId={{6F0B6D5C-3F2A-4C7B-9E11-2D8A4C6B5E31}
AppName=Agently
AppVersion=1.0.0
AppPublisher=Agently
DefaultDirName={localappdata}\Programs\Agently
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename={#OUTNAME}
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=app.ico
UninstallDisplayIcon={app}\Agently.exe
UninstallDisplayName=Agently ({#VARIANT})
WizardStyle=modern
ChangesAssociations=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#STAGEDIR}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Agently"; Filename: "{app}\Agently.exe"
Name: "{autodesktop}\Agently"; Filename: "{app}\Agently.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\Agently.exe"; Description: "Launch Agently"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
