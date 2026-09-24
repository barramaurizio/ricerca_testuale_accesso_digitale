@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Verifica allineamento versioni RTAD...
python tools\rtad_release.py check
echo.
pause