@echo off
echo ========================================
echo  Smart Food Ordering System Launcher
echo ========================================
echo Starting backend and frontend servers...
echo Press Ctrl+C to stop both servers
echo.

REM Change to project root directory
cd /d "%~dp0"

REM Start backend server in background
echo Starting FastAPI backend...
start "FastAPI Backend" cmd /c "cd fastapi_backend && python main.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend in background
echo Starting Next.js frontend...
start "Next.js Frontend" cmd /c "cd web_frontend && npm run dev"

echo.
echo ========================================
echo Both servers are now running!
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo ========================================
echo.
echo Press any key to stop both servers...

pause > nul

echo.
echo Stopping servers...

REM Kill backend process
taskkill /F /FI "WINDOWTITLE eq FastAPI Backend*" /T > nul 2>&1

REM Kill frontend process
taskkill /F /FI "WINDOWTITLE eq Next.js Frontend*" /T > nul 2>&1

REM Also try to kill any remaining python and node processes (be careful)
REM taskkill /F /IM python.exe > nul 2>&1
REM taskkill /F /IM node.exe > nul 2>&1

echo Servers stopped.
echo Press any key to exit...
pause > nul