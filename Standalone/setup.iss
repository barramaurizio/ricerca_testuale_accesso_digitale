[Setup]
AppId={{8F24C28D-4D3A-421A-93B4-855584C1C400}}
AppName=Ricerca Testuale Accesso Digitale
AppVersion=1.4.4
AppPublisher=Maurizio Barra (Accesso Digitale)
AppPublisherURL=https://paypal.me/AccessoDigitale
AppSupportURL=https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
AppUpdatesURL=https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
DefaultDirName={autopf}\Ricerca Testuale Accesso Digitale
DefaultGroupName=Ricerca Testuale Accesso Digitale
DisableProgramGroupPage=yes
OutputBaseFilename=Setup_RicercaTestualeAccessoDigitale_v1.4.4
OutputDir=InstallerOutput
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Ricerca Testuale Accesso Digitale.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Ricerca Testuale Accesso Digitale"; Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"
Name: "{autodesktop}\Ricerca Testuale Accesso Digitale"; Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"; Tasks: desktopicon

[Registry]
; --- INTEGRAZIONE CARTELLE ---
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""

; --- INTEGRAZIONE DISCHI ---
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""

; --- INTEGRAZIONE SINGOLI FILE ---
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""

[Run]
Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"; Description: "{cm:LaunchProgram,Ricerca Testuale Accesso Digitale}"; Flags: nowait postinstall skipifsilent