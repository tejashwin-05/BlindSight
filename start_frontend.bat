@echo off
echo ========================================
echo   EcoSight Frontend Launcher
echo ========================================
echo.

cd frontend

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    echo.
)

echo Starting development server...
echo Frontend will be available at http://localhost:3000
echo.
call npm run dev

pause
