@echo off
cd "D:\project\4 2\app"
call .venv\Scripts\activate

echo Starting Flask backend...
start cmd /k "cd fastapi_backend && python main.py"

timeout /t 3 /nobreak > nul

echo Starting Next.js frontend...
start cmd /k "cd web_frontend && npm run dev"

echo Project started! Frontend: http://localhost:3000, Backend: http://localhost:8000