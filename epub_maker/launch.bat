@echo off
rem EPUB Maker launcher: start local server (if not running) and open browser
netstat -ano | findstr ":8400" | findstr "LISTENING" >nul
if errorlevel 1 (
  start "epub-maker-server" /min python -m http.server 8400 --directory "C:\youtube\epub_maker"
  ping -n 2 127.0.0.1 >nul
)
start "" http://localhost:8400/
