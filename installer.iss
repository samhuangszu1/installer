[Setup]
AppId={{E0C7D33D-7F03-4D4E-BDB4-CC2AA3E5A3A1}
AppName=HarmonyOS Installer
AppVersion=1.0.0
DefaultDirName={autopf}\HarmonyOSInstaller
DefaultGroupName=HarmonyOS Installer
OutputDir=installer_out
OutputBaseFilename=HarmonyOSInstaller_Setup
SetupIconFile=logo.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Files]
Source: "dist\HarmonyOSInstaller.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\settings.json"; DestDir: "{userappdata}\HarmonyOSInstaller"; Flags: onlyifdoesntexist ignoreversion
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\HarmonyOS Installer"; Filename: "{app}\HarmonyOSInstaller.exe"
Name: "{autodesktop}\HarmonyOS Installer"; Filename: "{app}\HarmonyOSInstaller.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\HarmonyOSInstaller.exe"; Description: "Launch HarmonyOS Installer"; Flags: nowait postinstall skipifsilent
