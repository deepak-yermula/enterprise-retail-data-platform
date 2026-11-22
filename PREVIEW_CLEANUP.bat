@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\cleanup_root_duplicates.ps1"
pause
