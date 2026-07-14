@echo off
rem Blog Niche Finder launcher: start Flask app (if not running) and open browser
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul
if errorlevel 1 (
  start "blog-niche-finder-server" /min python "C:\youtube\blog_niche_finder\app.py"
  ping -n 6 127.0.0.1 >nul
)
start "" http://127.0.0.1:5000/
