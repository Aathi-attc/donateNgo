@echo off
cd /d "%~dp0"
title donateNgo Server

netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
  echo Server already running on port 5000.
  echo Use stop_server.bat to stop it, or open http://127.0.0.1:5000
  pause
  exit /b
)

echo ==============================
echo   donateNgo - starting server
echo ==============================
echo.
python app.py
pause
