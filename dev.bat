@echo off
setlocal enabledelayedexpansion

:: Provisioning Station - Development Mode
:: Runs backend and frontend in development mode
:: Usage: dev.bat [--no-reload]

set BACKEND_PORT=3260
set FRONTEND_PORT=5173
set PROJECT_DIR=%~dp0
set USE_RELOAD=1

:: Check for --no-reload argument
if "%1"=="--no-reload" set USE_RELOAD=0
if "%1"=="-n" set USE_RELOAD=0

if %USE_RELOAD%==1 (
    echo ==========================================
    echo   Provisioning Station - Dev Mode
    echo   [Hot Reload Enabled]
    echo ==========================================
) else (
    echo ==========================================
    echo   Provisioning Station - Dev Mode
    echo   [No Hot Reload - Better Windows Support]
    echo ==========================================
)
echo.

:: Check dependencies
echo [1/4] Checking dependencies...

where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: uv is not installed
    exit /b 1
)

where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: npm is not installed
    exit /b 1
)

:: Sync Python dependencies
echo [2/4] Syncing Python dependencies...
cd /d "%PROJECT_DIR%"
uv sync --quiet
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to sync Python dependencies
    exit /b 1
)

:: Install frontend dependencies if needed
echo [3/4] Checking frontend dependencies...
cd /d "%PROJECT_DIR%frontend"
if not exist "node_modules" (
    echo Installing npm packages...
    npm install --silent
)

:: Start backend server
echo [4/4] Starting servers...
echo.

cd /d "%PROJECT_DIR%"
if %USE_RELOAD%==1 (
    start "Backend" cmd /c "uv run uvicorn provisioning_station.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --loop asyncio"
) else (
    start "Backend" cmd /c "uv run uvicorn provisioning_station.main:app --host 0.0.0.0 --port %BACKEND_PORT% --loop asyncio"
)

:: Wait a moment for backend to start
timeout /t 2 /nobreak >nul

:: Start frontend dev server
cd /d "%PROJECT_DIR%frontend"
start "Frontend" cmd /c "npm run dev -- --port %FRONTEND_PORT%"

:: Wait a moment for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo   Development servers running!
echo.
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   API:      http://localhost:%BACKEND_PORT%/api
echo.
echo   Close the Backend and Frontend windows
echo   to stop the servers, or press any key
echo   here to stop all servers.
echo ==========================================
echo.

pause >nul

:: Cleanup - kill the server windows
echo.
echo Shutting down servers...
taskkill /FI "WINDOWTITLE eq Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /F >nul 2>&1

:: Also try to kill by port if the above doesn't work
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo All servers stopped.
endlocal
