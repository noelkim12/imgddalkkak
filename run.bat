@echo off
title Image Background Remover

echo ====================================
echo    Image Background Remover v1.0
echo ====================================
echo.

echo Checking Python version...
python --version
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.7+ and add to PATH.
    echo.
    pause
    exit /b 1
)

echo.
echo Checking required packages...
python -c "import rembg; print('rembg: OK')" 2>nul || (
    echo Installing rembg package...
    pip install rembg
)

python -c "import PIL; print('PIL: OK')" 2>nul || (
    echo Installing Pillow package...
    pip install pillow
)

python -c "import tkinterdnd2; print('tkinterdnd2: OK')" 2>nul || (
    echo Installing tkinterdnd2 package...
    pip install tkinterdnd2
)

echo.
echo Checking Alpha Matting dependencies (optional)...
python -c "import pymatting, cv2, scipy; print('Alpha Matting: OK')" 2>nul || (
    echo Alpha Matting dependencies not found - will be installed automatically when needed
)

echo.
echo Starting program...
echo.

python "%~dp0remove_bg.py"

REM GUI 창이 닫히면 자동으로 bat 프로세스도 종료