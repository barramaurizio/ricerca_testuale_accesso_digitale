[Setup]
AppId={{8F24C28D-4D3A-421A-93B4-855584C1C400}}
AppName=Ricerca Testuale Accesso Digitale
AppVersion=2.0.8
AppPublisher=Maurizio Barra (Accesso Digitale)
AppPublisherURL=https://paypal.me/AccessoDigitale
AppSupportURL=https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
AppUpdatesURL=https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
DefaultDirName={autopf}\Ricerca Testuale Accesso Digitale
DefaultGroupName=Ricerca Testuale Accesso Digitale
DisableProgramGroupPage=yes
OutputBaseFilename=Setup_RicercaTestualeAccessoDigitale_v2.0.8
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
; Marker canale Installer (updater SA 1.7.6+): non dipende solo da Program Files / unins000
Source: "rtad_install_channel.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Ricerca Testuale Accesso Digitale"; Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"
Name: "{autodesktop}\Ricerca Testuale Accesso Digitale"; Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"; Tasks: desktopicon
; Invia a (shell:sendto): collegamento vivo, segue gli aggiornamenti. Non è la copia dell'exe.
Name: "{userappdata}\Microsoft\Windows\SendTo\Ricerca Testuale Accesso Digitale"; Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"
Name: "{userappdata}\Microsoft\Windows\SendTo\Riproduttore RTAD"; Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"; Parameters: "--play"

[Registry]
; --- INTEGRAZIONE CARTELLE ---
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
; Batch immagini cartella (1.6.6)
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitaleBatch"; ValueType: string; ValueData: "Analizza immagini di questa cartella (Accesso Digitale)"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitaleBatch"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitaleBatch\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --batch-folder ""%1"""
; Batch audio/video cartella (1.7.2)
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitaleBatchMedia"; ValueType: string; ValueData: "Analizza audio/video di questa cartella (Accesso Digitale)"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitaleBatchMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Directory\shell\RicercaTestualeAccessoDigitaleBatchMedia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --batch-media-folder ""%1"""

; --- INTEGRAZIONE DISCHI ---
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitaleBatch"; ValueType: string; ValueData: "Analizza immagini di questa cartella (Accesso Digitale)"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitaleBatch"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitaleBatch\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --batch-folder ""%1"""
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitaleBatchMedia"; ValueType: string; ValueData: "Analizza audio/video di questa cartella (Accesso Digitale)"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitaleBatchMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\Drive\shell\RicercaTestualeAccessoDigitaleBatchMedia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --batch-media-folder ""%1"""

; --- FILE GENERICI (non immagini / non documenti col sottomenù) ---
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueType: string; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale"; ValueName: "AppliesTo"; ValueType: string; ValueData: "System.Kind:<>System.Kind#Picture AND System.FileExtension:<>.pdf AND System.FileExtension:<>.docx AND System.FileExtension:<>.xlsx AND System.FileExtension:<>.odt AND System.FileExtension:<>.txt AND System.FileExtension:<>.md AND System.FileExtension:<>.epub AND System.FileExtension:<>.html AND System.FileExtension:<>.htm AND System.FileExtension:<>.rtf AND System.FileExtension:<>.csv AND System.FileExtension:<>.log AND System.FileExtension:<>.mp3 AND System.FileExtension:<>.wav AND System.FileExtension:<>.m4a AND System.FileExtension:<>.flac AND System.FileExtension:<>.ogg AND System.FileExtension:<>.mp4 AND System.FileExtension:<>.mkv AND System.FileExtension:<>.webm AND System.FileExtension:<>.avi AND System.FileExtension:<>.mov"
Root: HKCU; Subkey: "Software\Classes\*\shell\RicercaTestualeAccessoDigitale\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" ""%1"""

; --- SOTTOMENÙ IMMAGINI (SystemFileAssociations) ---
; .jpg
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

; .jpeg
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

; .png
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

; .gif / .webp / .bmp / .tif / .tiff / .jfif / .ico
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri"; ValueType: string; ValueData: "Apri / analizza questa immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi"; ValueType: string; ValueData: "Descrivi immagine (dettagliata)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\02descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'immagine"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr"; ValueType: string; ValueData: "Leggi testo nell'immagine (OCR)"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\03ocr\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ocr-quick ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette"; ValueType: string; ValueData: "Etichette e oggetti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\04etichette\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --labels ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\05scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia"; ValueType: string; ValueData: "Copia descrizione"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\06copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-describe ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\08taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --image-clip ""%1"""

; --- SOTTOMENÙ PDF (documento + immagini nel PDF) ---
; Rimuove la vecchia voce 02descrivi (1.6.5 prima iterazione) in upgrade.
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\02descrivi"; Flags: deletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\01apri"; ValueType: string; ValueData: "Apri questo PDF"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del PDF"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-pdf ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\03copia"; ValueType: string; ValueData: "Copia testo del PDF"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-pdf-text ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\04descrivi"; ValueType: string; ValueData: "Descrivi immagini del PDF"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\04descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-pdf ""%1"""

; --- SOTTOMENÙ DOCUMENTI (Apri / Leggi testo / Copia testo) ---

; .docx
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

; .xlsx (1.7.4 — allineato ai documenti dopo ricerca celle 1.7.3)
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo foglio di calcolo"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del foglio"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del foglio"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""


; .odt
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

; .txt
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

; .md
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

; .epub
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

; .html / .htm
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

; .rtf / .csv / .log
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri"; ValueType: string; ValueData: "Apri questo documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --open-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi"; ValueType: string; ValueData: "Leggi testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\02leggi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --read-doc ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia"; ValueType: string; ValueData: "Copia testo del documento"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\03copia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --copy-doc-text ""%1"""


; --- SOTTOMENU AUDIO/VIDEO (1.6.7) ---
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.mp3; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.wav; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.m4a; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.flac; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.ogg; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.mp4; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.mkv; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.webm; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.avi; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Cerca con Accesso Digitale"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "Icon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia"; ValueName: "SubCommands"; ValueType: string; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\00riproduci\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
.mov; ValueType: string; ValueData: "Apri / analizza questo audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\01apri\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto"; ValueType: string; ValueData: "Tutto sull'audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\02tutto\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-all ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi"; ValueType: string; ValueData: "Riassunto audio/video"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\03descrivi\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --describe-media ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda"; ValueType: string; ValueData: "Scheda tecnica"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\04scheda\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --media-tech ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia"; ValueType: string; ValueData: "Taglia e unisci"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\05taglia\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --clip ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti"; ValueType: string; ValueData: "Converti"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\06converti\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --convert ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\RicercaTestualeAccessoDigitaleImg\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\RicercaTestualeAccessoDigitalePdf\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.odt\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.md\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.epub\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.html\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.htm\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.rtf\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.log\shell\RicercaTestualeAccessoDigitaleDoc\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini"; ValueType: string; ValueData: "Chiedi a Gemini"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\RicercaTestualeAccessoDigitaleMedia\shell\09gemini\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --ask-gemini ""%1"""


; --- RIPRODUTTORE: ProgID per Apri con / Sempre o Solo una volta (solo audio-video) ---
; Il comando Applications generale (documenti/immagini) resta senza --play, nel [Code].
Root: HKCU; Subkey: "Software\Classes\RTAD.AudioVideo"; ValueType: string; ValueData: "Riproduttore RTAD (Accesso Digitale)"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\RTAD.AudioVideo\DefaultIcon"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"",0"
Root: HKCU; Subkey: "Software\Classes\RTAD.AudioVideo\shell\open"; ValueType: string; ValueData: "Riproduci con RTAD"
Root: HKCU; Subkey: "Software\Classes\RTAD.AudioVideo\shell\open\command"; ValueType: string; ValueData: """{app}\Ricerca Testuale Accesso Digitale.exe"" --play ""%1"""
Root: HKCU; Subkey: "Software\RTAD\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "Riproduttore RTAD"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\RTAD\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Riproduttore audio e video di Ricerca Testuale Accesso Digitale"
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "RTAD Riproduttore"; ValueData: "Software\RTAD\Capabilities"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mp3\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp3"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.wav\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".wav"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.m4a\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m4a"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.flac\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".flac"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.ogg\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ogg"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.mp4\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp4"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.mkv\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mkv"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.webm\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".webm"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.avi\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".avi"; ValueData: "RTAD.AudioVideo"
Root: HKCU; Subkey: "Software\Classes\.mov\OpenWithProgids"; ValueType: string; ValueName: "RTAD.AudioVideo"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\RTAD\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mov"; ValueData: "RTAD.AudioVideo"

[Code]
const
  RTADOpenWithExe = 'Ricerca Testuale Accesso Digitale.exe';

function RTADOpenWithExtensions: TStringList;
begin
  Result := TStringList.Create;
  Result.CommaText :=
    '.epub,.pdf,.docx,.doc,.odt,.xlsx,.txt,.md,.csv,.log,.rtf,.html,.htm,' +
    '.jpg,.jpeg,.jfif,.png,.bmp,.gif,.tif,.tiff,.webp,.ico,' +
    '.mp3,.m4a,.m4b,.aac,.flac,.ogg,.opus,.wav,.wma,.aif,.aiff,.mka,' +
    '.mp4,.m4v,.mkv,.avi,.mov,.wmv,.webm,.flv,.mts,.m2ts,.mpg,.mpeg,.3gp';
end;

procedure RTADRegisterOpenWith;
var
  Exts: TStringList;
  I: Integer;
  Cmd: String;
  AppKey: String;
begin
  { Compare nell'elenco Apri con. Non diventa il programma predefinito:
    Solo una volta e Sempre li sceglie la persona, in Windows. }
  Cmd := '"' + ExpandConstant('{app}\') + RTADOpenWithExe + '" "%1"';
  AppKey := 'Software\Classes\Applications\' + RTADOpenWithExe;
  RegWriteStringValue(HKCU, AppKey, 'FriendlyAppName', 'Ricerca Testuale Accesso Digitale');
  RegWriteStringValue(HKCU, AppKey + '\shell\open\command', '', Cmd);
  Exts := RTADOpenWithExtensions;
  try
    for I := 0 to Exts.Count - 1 do
    begin
      RegWriteStringValue(
        HKCU,
        'Software\Classes\' + Exts[I] + '\OpenWithList\' + RTADOpenWithExe,
        '',
        ''
      );
      RegWriteStringValue(HKCU, AppKey + '\SupportedTypes', Exts[I], '');
    end;
  finally
    Exts.Free;
  end;
end;

procedure RTADUnregisterOpenWith;
var
  Exts: TStringList;
  I: Integer;
begin
  RegDeleteKeyIncludingSubkeys(
    HKCU, 'Software\Classes\Applications\' + RTADOpenWithExe
  );
  RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\RTAD.AudioVideo');
  RegDeleteKeyIncludingSubkeys(HKCU, 'Software\RTAD');
  if RegValueExists(HKCU, 'Software\RegisteredApplications', 'RTAD Riproduttore') then
    RegDeleteValue(HKCU, 'Software\RegisteredApplications', 'RTAD Riproduttore');
  Exts := RTADOpenWithExtensions;
  try
    for I := 0 to Exts.Count - 1 do
      RegDeleteKeyIncludingSubkeys(
        HKCU,
        'Software\Classes\' + Exts[I] + '\OpenWithList\' + RTADOpenWithExe
      );
  finally
    Exts.Free;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RTADRegisterOpenWith;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RTADUnregisterOpenWith;
end;

[Run]
Filename: "{app}\Ricerca Testuale Accesso Digitale.exe"; Description: "{cm:LaunchProgram,Ricerca Testuale Accesso Digitale}"; Flags: nowait postinstall skipifsilent
