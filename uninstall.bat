@echo off
echo Uninstalling TSXS Polar Alignment...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Uninstall
pause
