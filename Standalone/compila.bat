@echo off
echo ======================================================
echo Compilazione Ricerca Testuale Accesso Digitale v1.5.3
echo ======================================================

REM Prerequisito: pip install feedparser pyinstaller wxPython pywin32
REM feedparser va incluso esplicitamente nell'exe (--hidden-import)

REM 1. Compilazione Standalone Portatile (File singolo .exe pronto all'uso)
echo.
echo [1/2] Creazione eseguibile Standalone (OneFile)...
pyinstaller --noconfirm --onefile --windowed --version-file "version.txt" --hidden-import=feedparser --collect-submodules=feedparser --name "Ricerca Testuale Accesso Digitale" app_gui.py

REM 2. Compilazione Cartella per eventuale Setup Inno Setup
echo.
echo [2/2] Creazione build per Inno Setup (OneDir)...
pyinstaller --noconfirm --onedir --windowed --version-file "version.txt" --hidden-import=feedparser --collect-submodules=feedparser --name "Ricerca Testuale Accesso Digitale" app_gui.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo PyInstaller completato! Ricerca Inno Setup per creare il file di installazione...
    powershell -Command "$iscc = (Get-ChildItem -Path 'C:\Program Files*', '$env:LOCALAPPDATA\Programs' -Filter 'ISCC.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName; if ($iscc) { Write-Host 'Inno Setup trovato in:' $iscc; & $iscc setup.iss } else { Write-Host 'ISCC.exe non rilevato: verra mantenuto solo l eseguibile in dist' }"
    echo.
    echo ======================================================
    echo Operazione conclusa con successo!
    echo ======================================================
) else (
    echo.
    echo [ERRORE] Compilazione PyInstaller fallita.
)
pause