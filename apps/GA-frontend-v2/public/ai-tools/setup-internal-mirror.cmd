@echo off
setlocal
chcp 65001 >nul
set "PS1=%~dp0setup-internal-mirror.ps1"
if not exist "%PS1%" (
  echo [fail] setup-internal-mirror.ps1 not found next to this file.
  pause
  exit /b 3
)

set "NOPAUSE="
for %%A in (%*) do (
  if /i "%%~A"=="-NoPause" set "NOPAUSE=1"
)

echo ==============================================================
echo  DSH / pip / npm  mirror source switch  (internal hub)
echo --------------------------------------------------------------
echo  Default hub comes from -HubBase in the .ps1. Override it:
echo    setup-internal-mirror.cmd -HubBase http://172.16.234.96:8081
echo  Preview only, write nothing:
echo    setup-internal-mirror.cmd -HubBase http://172.16.234.96:8081 -DryRun
echo  Check connectivity + current sources, write nothing:
echo    setup-internal-mirror.cmd -HubBase http://172.16.234.96:8081 -CheckOnly
echo  Roll back to the earliest backup (pre-first-run state):
echo    setup-internal-mirror.cmd -Revert
echo ==============================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [done] exit code 0
) else (
  echo [exit code %RC%]
)
if not defined NOPAUSE pause
exit /b %RC%