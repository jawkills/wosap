# Wosap PySide6 Rewrite

## What changed

- Legacy Tkinter implementation was replaced by a new PySide6 app structure.
- New entrypoint is `wosap.py` -> `app.main.main()`.
- App now uses modular architecture:
  - `app/core/state.py`
  - `app/services/*.py`
  - `app/ui/main_window.py`
  - `app/ui/widgets/*.py`
  - `app/workers/transfer_worker.py`

## Feature coverage

Implemented parity-targeted behaviors:
- Folder picker + drag-and-drop folder
- Recursive `.tar.gz` scan and validation
- Device detection via `adb devices`
- Device selection and custom label persistence
- Destination base with `auto_date` / `manual` mode
- Preview dialog with per-device distribution
- Parallel transfer with `QThreadPool + QRunnable`
- Pause/resume (cooperative) and per-device + total progress
- Continue-on-failure with end-of-run summary

## Styling

- Light soft modern style in `app/resources/styles/light_soft.qss`.

## Verification run

- Syntax verification completed:
  - `python -m compileall app wosap.py`
- Runtime dependency check:
  - `python -c "import PySide6; print(PySide6.__version__)"`
  - Result: `ModuleNotFoundError: No module named 'PySide6'`

## Next action required

Install PySide6 in the target environment before launching:

```bash
python -m pip install PySide6
```

## Packaging workflow (optimized)

A slimmer build flow is now provided via `build.bat`:

```bash
build.bat
```

What it does:
- Uses `pyinstaller` in `--windowed` mode.
- Injects Windows version metadata from `packaging/version_info.txt`.
- Bundles `app/resources` so QSS/theme files are available at runtime.
- Uses `assets/wosap.ico` automatically if present.

Output:
- `dist/Wosap/Wosap.exe`

Current build footprint (latest run):
- EXE: ~1.63 MB
- Full `dist/Wosap`: ~118.34 MB

## Versioning and icon convention

- EXE version metadata is currently set to `1.0.1.0` in `packaging/version_info.txt`.
- For custom branding icon, place file at `assets/wosap.ico` then run `build.bat`.

## Default RST icon

A default RST logo icon has been generated:
- `assets/wosap.ico` (used automatically by `build.bat`)
- `assets/wosap.png` (visual preview)
- `assets/generate_rst_icon.py` (script to regenerate icon)

Build was rerun and `dist/Wosap/Wosap.exe` now uses the RST icon.

## Icon style update

The default RST icon style has been changed to **outline** and rebuilt into the executable.

## Installer package (Inno Setup)

Added installer packaging files:
- `packaging/WosapInstaller.iss`
- `packaging/build_installer.py`
- `build-installer.bat`

Build command:

```bat
build-installer.bat
```

Notes:
- Script builds app bundle first (`build.bat`).
- Requires **Inno Setup 6** (`ISCC.exe`) installed.
- If `ISCC.exe` is not found, script prints install link and exits.
