@echo off
echo ========================================
echo   EcoSight Server - Quick Start
echo ========================================
echo.

cd server

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

echo.
echo Starting EcoSight Server...
echo Press Ctrl+C to stop
echo.

set ECOSIGHT_HEADLESS=1
python main.py

pause
