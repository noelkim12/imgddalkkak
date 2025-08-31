@echo off
title Image Background Remover - Restart Helper

echo ====================================
echo    Restarting Application...
echo ====================================
echo.

echo Waiting for application to close...
timeout /t 2 /nobreak > nul

echo Starting application...
python "%~dp0remove_bg.py"

echo.
echo Application closed.
pause