@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0visualisierung\index.html" goto open
if not exist "%~dp0.venv\Scripts\python.exe" goto missing_python
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\export_visualization.py"
if errorlevel 1 goto failed
:open
start "" "%~dp0visualisierung\index.html"
exit /b 0
:missing_python
echo Bitte zuerst gemaess README.md installieren und die Baseline ausfuehren.
pause
exit /b 1
:failed
echo Der Export konnte nicht abgeschlossen werden. Hinweise stehen oben.
pause
exit /b 1
