@echo off
setlocal
python packaging\build_installer.py
exit /b %errorlevel%
