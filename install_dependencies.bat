@echo off
echo ========================================
echo   EcoSight - Install Dependencies
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

echo.
echo [1/3] Installing Server dependencies...
cd server
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNING: Some server dependencies failed to install
    echo You may need to install Visual Studio Build Tools
    echo.
)
cd ..

echo.
echo [2/3] Installing MCP Server dependencies...
cd mcp_server
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNING: Some MCP server dependencies failed to install
    echo.
)
cd ..

echo.
echo [3/3] Installing Flutter dependencies...
cd client
flutter pub get
if errorlevel 1 (
    echo.
    echo WARNING: Flutter dependencies failed
    echo Make sure Flutter SDK is installed and in PATH
    echo.
)
cd ..

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Configure API keys in mcp_server/.env
echo 2. Run start_server.bat to start the main server
echo 3. Run start_mcp_server.bat to start the MCP server
echo 4. Run 'cd client && flutter run' to start the app
echo.
pause
