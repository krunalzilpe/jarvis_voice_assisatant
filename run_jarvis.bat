@echo off
setlocal
set ROOT=%~dp0

if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" "%ROOT%Jarvis\jarvis.py"
  exit /b %errorlevel%
)

if exist "%ROOT%..\.venv\Scripts\python.exe" (
  "%ROOT%..\.venv\Scripts\python.exe" "%ROOT%Jarvis\jarvis.py"
  exit /b %errorlevel%
)

python "%ROOT%Jarvis\jarvis.py"
exit /b %errorlevel%
