@echo off
echo Starting Facebook Work Notifier Dashboard...
echo.
echo [1/2] Starting Backend API...
start "Backend API" cmd /k "cd backend && uvicorn app.main:app --reload --port 8001"
timeout /t 3 /nobreak > nul
echo.
echo [2/2] Starting Frontend Dashboard...
start "Frontend Dashboard" cmd /k "cd frontend && npm run dev"
echo.
echo ======================================
echo Dashboard starting up...
echo Backend: http://localhost:8001
echo Frontend: http://localhost:5174
echo ======================================
echo.
echo Press any key to stop all servers...
pause > nul

echo.
echo Stopping servers...
taskkill /FI "WindowTitle eq Backend API*" /T /F > nul 2>&1
taskkill /FI "WindowTitle eq Frontend Dashboard*" /T /F > nul 2>&1
echo Done!
