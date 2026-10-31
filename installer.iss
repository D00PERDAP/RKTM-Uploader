#define AppVersion "5.0.1"
[Setup]
AppId={{89DA7779-6E8E-44F1-9E8C-BB23FF136208}
AppName=РКТМ — Расписание
UninstallDisplayName=РКТМ — Расписание
AppPublisher=Сорокин Дмитрий Денисович
AppVersion={#AppVersion}
VersionInfoCompany=Сорокин Дмитрий Денисович
VersionInfoDescription=РКТМ — единое приложение расписания
VersionInfoVersion=5.0.1
DefaultDirName={autopf}\RKTM Schedule
DefaultGroupName=РКТМ — Расписание
OutputDir=release
OutputBaseFilename=RKTM-Setup-5.0.1-x86
MinVersion=6.1sp1
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
WizardImageFile=assets\setup-welcome.bmp
WizardSmallImageFile=assets\setup-logo.bmp
WizardImageStretch=yes
WizardImageBackColor=$00221FE5
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
Uninstallable=yes
SetupIconFile=assets\upload.ico
PrivilegesRequired=lowest
ArchitecturesAllowed=x86 x64
UninstallDisplayIcon={app}\Uploader\RKTM-Uploader.exe
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
[Files]
Source: "dist\RKTM-Uploader\*"; DestDir: "{app}\Uploader"; Flags: recursesubdirs createallsubdirs ignoreversion
[InstallDelete]
Type: files; Name: "{autodesktop}\РКТМ — Администратор.lnk"
Type: files; Name: "{group}\РКТМ — Администратор.lnk"
[Icons]
Name: "{autodesktop}\РКТМ — Расписание"; Filename: "{app}\Uploader\RKTM-Uploader.exe"; WorkingDir: "{app}\Uploader"; Tasks: desktopicon
Name: "{group}\РКТМ — Расписание"; Filename: "{app}\Uploader\RKTM-Uploader.exe"; WorkingDir: "{app}\Uploader"
[Run]
Filename: "{app}\Uploader\RKTM-Uploader.exe"; Description: "Открыть РКТМ — Расписание"; Flags: postinstall nowait skipifsilent

[Messages]
WelcomeLabel1=Установка РКТМ — Расписание
WelcomeLabel2=Единое приложение для публикации расписания колледжа.%n%nРасписание, история загрузок и настройки — в одном окне.%n%nНажмите «Далее», чтобы продолжить.
FinishedHeadingLabel=РКТМ — Расписание установлено
FinishedLabel=Приложение готово к работе.%n%nПри первом запуске откройте «Настройки», проверьте подключение и сохраните папку публикации.
[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Font.Color := $00221FE5;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
  WizardForm.PageNameLabel.Font.Color := $00221FE5;
  WizardForm.FinishedHeadingLabel.Font.Color := $00221FE5;
end;
