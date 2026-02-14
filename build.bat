@echo off
setlocal

set "APP_NAME=Wosap"
set "ENTRY=wosap.py"
set "VERSION_FILE=packaging\version_info.txt"
set "DATA_ARG=--add-data app\resources;app\resources"
set "ICON_ARG="

if exist "assets\wosap.ico" (
  set "ICON_ARG=--icon assets\wosap.ico"
)

echo [Wosap] Building %APP_NAME%...
python -m PyInstaller --noconfirm --clean --windowed --name "%APP_NAME%" --version-file "%VERSION_FILE%" %DATA_ARG% %ICON_ARG% "%ENTRY%"
if errorlevel 1 (
  echo [Wosap] Build failed.
  exit /b 1
)

echo [Wosap] Build done: dist\%APP_NAME%\%APP_NAME%.exe
exit /b 0
