; Inno Setup installer for DriveDesk.
#define AppName "DriveDesk"
#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif
#define AppPublisher "Work with Yuvraj Garg"
#define AppExeName "DriveDesk.exe"

[Setup]
AppId={{B7E5B4E8-1E4C-4A11-9AF8-5D3B6BFE4D6B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\DriveDesk
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\dist\installer
OutputBaseFilename=DriveDesk-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\DriveDesk.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\third_party\rclone.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DriveDesk"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\DriveDesk"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch DriveDesk"; Flags: nowait postinstall skipifsilent
