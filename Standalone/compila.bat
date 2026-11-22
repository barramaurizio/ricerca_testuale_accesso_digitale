@echo off
echo ======================================================
echo Compilazione Ricerca Testuale Accesso Digitale v2.0.9
echo ======================================================

REM Prerequisiti Python (stessa python del PATH):
REM   pip install -r requirements-standalone.txt
REM   pip install -r requirements-ocr-easy.txt
REM EasyOCR e' importato in try/except: senza --collect-all PyInstaller lo salta
REM e l'exe resta ~20 MB invece dei ~250 MB delle release GitHub (buco PC nuovo 20/11/2026).
REM Verifica prima: python -c "import easyocr, torch; print(easyocr.__version__, torch.__version__)"

python -c "import easyocr, torch" 2>nul
if errorlevel 1 (
    echo.
    echo [ERRORE] EasyOCR/torch non importabili in questa Python.
    echo Esegui: pip install -r requirements-ocr-easy.txt
    echo Poi rilancia compila.bat. Senza di loro l'exe resta ~20 MB.
    pause
    exit /b 1
)

REM feedparser e EasyOCR/torch vanno inclusi esplicitamente

REM 1. Compilazione Standalone Portatile (File singolo .exe pronto all'uso)
echo.
echo [1/2] Creazione eseguibile Standalone (OneFile)...
pyinstaller --noconfirm --onefile --windowed --version-file "version.txt" --add-binary "nvdaControllerClient64.dll;." --hidden-import=feedparser --hidden-import=rtad_attach_dialog --hidden-import=rtad_whisper --hidden-import=rtad_reading_mark --hidden-import=easyocr --hidden-import=torch --collect-all easyocr --collect-all torch --collect-submodules=feedparser --name "Ricerca Testuale Accesso Digitale" app_gui.py

REM 2. Compilazione Cartella per eventuale Setup Inno Setup
echo.
echo [2/2] Creazione build per Inno Setup (OneDir)...
pyinstaller --noconfirm --onedir --windowed --version-file "version.txt" --add-binary "nvdaControllerClient64.dll;." --hidden-import=feedparser --hidden-import=rtad_attach_dialog --hidden-import=rtad_whisper --hidden-import=rtad_reading_mark --hidden-import=easyocr --hidden-import=torch --collect-all easyocr --collect-all torch --collect-submodules=feedparser --name "Ricerca Testuale Accesso Digitale" app_gui.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo PyInstaller completato! Ricerca Inno Setup per creare il file di installazione...
    powershell -Command "$iscc = (Get-ChildItem -Path 'C:\Program Files*', '$env:LOCALAPPDATA\Programs' -Filter 'ISCC.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName; if ($iscc) { Write-Host 'Inno Setup trovato in:' $iscc; & $iscc setup.iss } else { Write-Host 'ISCC.exe non rilevato: verra mantenuto solo l eseguibile in dist' }"
    echo.
    echo Controlla i MB: Portable/Setup devono essere ~200-250 MB come su GitHub, non ~20 MB.
    echo ======================================================
    echo Operazione conclusa con successo!
    echo ======================================================
) else (
    echo.
    echo [ERRORE] Compilazione PyInstaller fallita.
)
pause
