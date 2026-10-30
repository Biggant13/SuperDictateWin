; Скрипт для создания установщика SuperDictate
; Требуется Inno Setup 6+

#define MyAppName "SuperDictate"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "Biggant13"
#define MyAppURL "https://github.com/Biggant13/SuperDictateWin"
#define MyAppExeName "SuperDictate.exe"

[Setup]
; AppId — уникальный идентификатор. Не меняй его, если будешь обновлять программу!
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Сжатие
Compression=lzma2/ultra64
SolidCompression=yes
; Установка только для текущего пользователя (не требует прав админа для установки в AppData)
PrivilegesRequired=lowest
; Если хочешь ставить в Program Files, раскомментируй строку ниже и закомментируй верхнюю
; PrivilegesRequired=admin
OutputDir=dist_installer
OutputBaseFilename=SuperDictate-Setup-{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Галочка "Создать ярлык на рабочем столе" (по умолчанию выключена, но пользователь может включить)
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Копируем ВСЁ содержимое папки dist/SuperDictate (включая _internal и exe)
Source: "dist\SuperDictate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлык в меню Пуск
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Ярлык на рабочем столе (только если пользователь выбрал задачу)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Предложить запустить программу после установки
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent