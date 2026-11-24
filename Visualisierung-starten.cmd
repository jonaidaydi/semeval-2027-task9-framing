@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto missing_python
"%~dp0.venv\Scripts\python.exe" "%~dp0projekt.py" anzeigen
if errorlevel 1 goto failed
exit /b 0
:missing_python
echo Bitte zuerst im Projektordner: py.exe -3.13 projekt.py einrichten
pause
exit /b 1
:failed
echo Die Visualisierung konnte nicht geoeffnet werden. Hinweise stehen oben.
pause
exit /b 1
