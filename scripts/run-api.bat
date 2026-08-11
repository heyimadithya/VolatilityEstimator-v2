@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0backend
call .venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
