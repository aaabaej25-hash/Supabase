@echo off
rem Essay Helper launcher: start local server (if not running) and open browser
netstat -ano | findstr ":8300" | findstr "LISTENING" >nul
if errorlevel 1 (
  start "essay-helper-server" /min python -m http.server 8300 --directory "C:\youtube\essay_helper"
  ping -n 2 127.0.0.1 >nul
)
start "" http://localhost:8300/
