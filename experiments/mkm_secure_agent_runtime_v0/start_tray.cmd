@echo off
setlocal
if "%MKM_AGENT_ROOTS%"=="" (
  echo MKM_AGENT_ROOTS is required.
  exit /b 2
)
if "%MKM_AGENT_STATE%"=="" (
  echo MKM_AGENT_STATE is required.
  exit /b 2
)
python "%~dp0tray_app.py"
