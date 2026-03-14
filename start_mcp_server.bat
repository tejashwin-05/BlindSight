@echo off
echo ========================================
echo   EcoSight MCP Server - Quick Start
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
echo Checking MCP server dependencies...
pip show mcp >nul 2>&1
if errorlevel 1 (
    echo Installing MCP server dependencies...
    pip install -r mcp_server/requirements.txt
)

echo.
echo Starting MCP Server (SSE mode for web clients)...
echo Server will be available at http://localhost:8100
echo Press Ctrl+C to stop
echo.

python -m mcp_server.server --sse --port 8100

pause
