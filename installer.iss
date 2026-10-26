#define AppVersion "4.2.0"
[Setup]
AppId={{89DA7779-6E8E-44F1-9E8C-BB23FF136208}
AppName=РКТМ — Расписание
AppVersion={#AppVersion}
DefaultDirName={autopf}\RKTM Schedule
DefaultGroupName=РКТМ — Расписание
OutputDir=release
OutputBaseFilename=RKTM-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
Uninstallable=yes
SetupIconFile=assets\upload.ico
PrivilegesRequired=admin
ArchitecturesAllowed=x86 x64
UninstallDisplayIcon={app}\Uploader\RKTM-Uploader.exe
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
[Files]
Source: "dist\RKTM-Admin\*"; DestDir: "{app}\Admin"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "dist\RKTM-Uploader\*"; DestDir: "{app}\Uploader"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{autodesktop}\РКТМ — Администратор"; Filename: "{app}\Admin\RKTM-Admin.exe"; IconFilename: "{app}\Admin\RKTM-Admin.exe"
Name: "{autodesktop}\РКТМ — Расписание"; Filename: "{app}\Uploader\RKTM-Uploader.exe"; IconFilename: "{app}\Uploader\RKTM-Uploader.exe"
Name: "{group}\РКТМ — Администратор"; Filename: "{app}\Admin\RKTM-Admin.exe"
Name: "{group}\РКТМ — Расписание"; Filename: "{app}\Uploader\RKTM-Uploader.exe"
[Run]
Filename: "{app}\Admin\RKTM-Admin.exe"; Description: "Настроить подключение РКТМ"; Flags: postinstall nowait skipifsilent
