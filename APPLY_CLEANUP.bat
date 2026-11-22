@echo off
echo This removes ONLY verified duplicate root files whose organized copies exist.
echo Please run PREVIEW_CLEANUP.bat first.
choice /C YN /M "Apply duplicate cleanup now?"
if errorlevel 2 exit /b
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\cleanup_root_duplicates.ps1" -Apply
pause
