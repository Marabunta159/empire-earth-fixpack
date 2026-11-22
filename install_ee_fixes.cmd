@echo off
setlocal
rem Empire Earth + Art of Conquest (NeoEE): Fix-Paket installieren / entfernen. Fragt per UAC nach Adminrechten.
rem
rem   install_ee_fixes.cmd                      alle Bausteine fuer Empire Earth und (falls vorhanden) Art of Conquest
rem   install_ee_fixes.cmd menu                 Bausteine per Nummer waehlen
rem   install_ee_fixes.cmd install units net    nur die genannten Bausteine
rem   install_ee_fixes.cmd status               was ist installiert
rem   install_ee_fixes.cmd uninstall [...]      alles bzw. die genannten Bausteine wieder entfernen
rem   install_ee_fixes.cmd noaoc                wie ohne Argument, aber nur Empire Earth
rem
rem   Bausteine: crash net fog aocstart cheats units fps      (Beschreibung: python ee_fixes.py list)
rem   Andere Ordner: ... --ee "<Ordner Empire Earth>" --aoc "<Ordner Art of Conquest>"
rem   Braucht Python 3.8 oder neuer (python.org), sonst nichts.

net session >nul 2>&1
if errorlevel 1 (
    if "%~1"=="" (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    ) else (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    )
    exit /b
)

cd /d "%~dp0"
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
where python >nul 2>&1 || where py >nul 2>&1 || set "PY=C:\Python313\python.exe"

if "%~1"=="" (
    %PY% ee_fixes.py install
) else if /I "%~1"=="noaoc" (
    %PY% ee_fixes.py install --only ee
) else (
    %PY% ee_fixes.py %*
)
echo.
pause
exit /b %errorlevel%
