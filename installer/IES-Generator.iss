; IES-Generator.iss — установщик «IES Generator Setup.exe» для Inno Setup 6.
;
; Файл сохранён в UTF-8 с BOM: Inno Setup 6 считает .iss без BOM файлом в
; системной кодировке, и кириллица в нём превратится в мусор. При правке
; в редакторе следите, чтобы BOM сохранялся.
;
; Собирается автоматически в GitHub Actions
; (.github/workflows/build-windows.yml). Вручную:
;
;   ISCC.exe /DAppVersion=1.2.0 ^
;            /DAppSourceDir=..\ies-generator\dist\app\IES_Generator ^
;            installer\IES-Generator.iss
;
; Все параметры ниже имеют значения по умолчанию, поэтому скрипт
; компилируется и без ключей /D — лишь бы сборка PyInstaller лежала
; по пути AppSourceDir.

#ifndef AppVersion
  #define AppVersion "1.2.0"
#endif

; Папка со сборкой PyInstaller в режиме --onedir: там лежит
; IES_Generator.exe и папка _internal со всем содержимым Python.
#ifndef AppSourceDir
  #define AppSourceDir "..\ies-generator\dist\app\IES_Generator"
#endif

; Папка, куда попадёт готовый установщик.
#ifndef OutputDir
  #define OutputDir "..\dist-installer"
#endif

#define AppName "IES Generator"
#define AppPublisher "ASTZ"
#define AppExeName "IES_Generator.exe"
#define ManualFile "..\ies-generator\Инструкция.md"
#define IconFile "icon.ico"

[Setup]
; AppId менять нельзя: по нему Windows опознаёт уже установленную
; программу при обновлении и удалении.
AppId={{18C6BA4C-7019-4F44-A6CD-2B4D6FB74F1D}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup

; Установка в профиль пользователя — права администратора и запрос UAC
; не нужны. При PrivilegesRequired=lowest {autopf} разворачивается в
; {localappdata}\Programs.
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; Страницу выбора папки не прячем: пользователь может выбрать свой путь,
; в том числе с пробелами и кириллицей — Inno Setup 6 полностью Unicode.
DisableDirPage=no
AllowNoIcons=yes

; Внутри лежит 64-разрядное приложение.
ArchitecturesAllowed=x64compatible

OutputDir={#OutputDir}
OutputBaseFilename=IES Generator Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}

#if FileExists(AddBackslash(SourcePath) + IconFile)
  SetupIconFile={#IconFile}
#endif

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Без флага unchecked галочка стоит по умолчанию.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Вся сборка PyInstaller целиком: .exe плюс папка _internal с Python,
; tkinter и openpyxl внутри. На компьютере пользователя ничего
; доустанавливать не нужно.
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ManualFile}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; WorkingDir — «Документы», чтобы диалоги сохранения открывались там,
; а не в папке установки.
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{userdocs}"
Name: "{group}\Инструкция"; Filename: "{app}\Инструкция.md"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; WorkingDir: "{userdocs}"; Flags: nowait postinstall skipifsilent
