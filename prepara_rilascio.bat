@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================================
echo RTAD - Preparazione rilascio (tool automatico)
echo ======================================================
echo.
echo Comandi utili:
echo   1. Verifica versioni allineate
echo   2. Bump versione (es. 1.5.2) + note template + .nvda-addon
echo   3. Solo ricostruisci Add-on
echo   4. Solo genera note di rilascio
echo   5. Riepilogo testi Commit / Release / Store
echo   0. Esci
echo.

set /p CHOICE=Scegli (0-5): 

if "%CHOICE%"=="1" goto CHECK
if "%CHOICE%"=="2" goto BUMP
if "%CHOICE%"=="3" goto ADDON
if "%CHOICE%"=="4" goto NOTES
if "%CHOICE%"=="5" goto SUMMARY
goto END

:CHECK
python tools\rtad_release.py check
goto END

:BUMP
set /p VER=Nuova versione (es. 1.5.2): 
if "%VER%"=="" goto END
python tools\rtad_release.py bump %VER%
goto END

:ADDON
python tools\rtad_release.py addon
goto END

:NOTES
set /p VER=Versione per le note (vuoto = quella attuale): 
if "%VER%"=="" (
  python tools\rtad_release.py notes
) else (
  python tools\rtad_release.py notes %VER%
)
goto END

:SUMMARY
set /p VER=Versione (vuoto = quella attuale): 
if "%VER%"=="" (
  python tools\rtad_release.py summary
) else (
  python tools\rtad_release.py summary %VER%
)
goto END

:END
echo.
pause