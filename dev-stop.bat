@echo off
:: Emergency stop script for dev servers
echo Stopping all dev servers...

:: Kill backend/frontend windows by title
taskkill /FI "WINDOWTITLE eq Backend*" /F 2>nul
taskkill /FI "WINDOWTITLE eq Frontend*" /F 2>nul

:: Kill by port 3260 (backend)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3260" ^| findstr "LISTENING"') do (
    echo Killing backend PID: %%a
    taskkill /PID %%a /F 2>nul
)

:: Kill by port 5173 (frontend)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo Killing frontend PID: %%a
    taskkill /PID %%a /F 2>nul
)

echo Done.
