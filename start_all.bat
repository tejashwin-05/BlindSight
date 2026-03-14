@echo off
echo ========================================
echo   BlindSight - Starting All Services
echo ========================================
echo.

echo Starting Main Server...
start "BlindSight Main Server" cmd /k "cd server && set ECOSIGHT_HEADLESS=1 && python main.py"

timeout /t 2 /nobreak >nul

echo Starting Frontend...
start "BlindSight Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Main Server: Running in background
echo Frontend: Check the new window for URL
echo.
echo Press any key to exit...
pause >nul
