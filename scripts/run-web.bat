@echo off
cd /d "%~dp0..\frontend"
call npx vite --host 127.0.0.1 --port 5173
