[Setup]
AppId={{8F24C28D-4D3A-421A-93B4-855584C1C400}}
AppName=Ricerca Testuale Accesso Digitale
AppVersion=1.6.4
AppPublisher=Maurizio Barra (Accesso Digitale)
AppPublisherURL=https://paypal.me/AccessoDigitale
AppSupportURL=https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
AppUpdatesURL=https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
DefaultDirName={autopf}\Ricerca Testuale Accesso Digitale
DefaultGroupName=Ricerca Testuale Accesso Digitale
DisableProgramGroupPage=yes
OutputBaseFilename=Setup_RicercaTestualeAccessoDigitale_v1.6.4
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

; --- FILE GENERICI (non immagini): apri in ricerca ---
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueName: "AppliesTo"; ValueType: string; ValueData: "System.Kind:<>System.Kind#Picture"
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""

; --- SOTTOMENÙ IMMAGINI (SystemFileAssociations) ---
; .jpg
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

; .jpeg
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

; .png
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

; .gif / .webp / .bmp / .tif / .tiff / .jfif / .ico
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri in Ricerca Testuale"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""

[Run]
Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"; Description: "{cm:LaunchProgram,Ricerca Testuale Accesso Digitale}"; Flags: nowait postinstall skipifsilent
