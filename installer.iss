#define MyAppName "Media Flow"
#ifndef MyAppVersion
  #define MyAppVersion "1.4.3"
#endif
#define MyAppPublisher "musicallyivan"
#define MyAppURL "https://github.com/musicallyivan/mediaflow"
#define MyAppExeName "media-flow.exe"
#define MyAppIcon "assets\installer\media-flow.ico"
#define MyWizardImage "assets\installer\wizard-image.bmp"
#define MyWizardSmallImage "assets\installer\wizard-small.bmp"

[Setup]
AppId={{D2B8B1A3-7B27-4C6B-BD3A-2D7B0F1D7F21}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile={#MyAppIcon}
WizardImageFile={#MyWizardImage}
WizardSmallImageFile={#MyWizardSmallImage}
OutputDir=build\installer
OutputBaseFilename=media-flow-setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
spanish.WelcomeLabel1=Bienvenido al instalador de [name]
spanish.WelcomeLabel2=Instalara Media Flow, un convertidor local para audio, video e imagen.%n%nSe recomienda cerrar la aplicacion antes de continuar.
english.WelcomeLabel1=Welcome to the [name] Setup Wizard
english.WelcomeLabel2=This will install Media Flow, a local converter for audio, video, and image files.%n%nIt is recommended that you close the app before continuing.

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos adicionales:"; Flags: unchecked

[Files]
Source: "release\media-flow\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\icon-300.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\media-flow\ffmpeg-licenses\*"; DestDir: "{app}\ffmpeg-licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
