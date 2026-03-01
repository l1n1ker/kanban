@echo off
setlocal

cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    echo Create virtual environment first.
    exit /b 1
)

start "PocketFlow Backend" cmd /k ""%PY%" -m uvicorn backend.http.app:app --host 127.0.0.1 --port 8000"

timeout /t 2 >nul

"%PY%" -m ui_tk.main

endlocal
