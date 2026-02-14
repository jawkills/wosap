# Wosap

Wosap is a Windows desktop app for distributing `.tar.gz` files to multiple Android devices using ADB.

## Features

- PySide6 desktop UI (light, compact layout)
- Recursive `.tar.gz` scan from source folder
- Multi-device selection and custom device labels
- Auto/manual destination path mode
- Transfer preview before execution
- Parallel push with pause/resume
- Per-device status + detailed log output
- Continue-on-failure summary

## Requirements

- Windows
- Python 3.12+
- ADB in PATH (Android Platform Tools)

## Run from source

```bash
python -m pip install -r requirements.txt
python wosap.py
```

## Build EXE

```bash
build.bat
```

Output:
- `dist/Wosap/Wosap.exe`

## Build Installer

Install Inno Setup 6 first, then:

```bash
build-installer.bat
```

Output:
- `installer/Wosap-Setup-1.0.1.exe`
