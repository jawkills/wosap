from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISS_PATH = ROOT / "packaging" / "WosapInstaller.iss"


def find_iscc() -> Path | None:
    from_path = shutil.which("iscc")
    if from_path:
        return Path(from_path)

    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def run() -> int:
    if not ISS_PATH.exists():
        print(f"[Wosap] Missing Inno Setup script: {ISS_PATH}")
        return 1

    print("[Wosap] Building application bundle first...")
    subprocess.run(["cmd", "/c", "build.bat"], check=True, cwd=ROOT)

    iscc = find_iscc()
    if not iscc:
        print("[Wosap] Inno Setup (ISCC.exe) not found.")
        print("[Wosap] Install Inno Setup 6, then rerun this script.")
        print("[Wosap] Download: https://jrsoftware.org/isdl.php")
        return 1

    print(f"[Wosap] Building installer with {iscc} ...")
    subprocess.run([str(iscc), str(ISS_PATH)], check=True, cwd=ROOT)
    print("[Wosap] Installer done. Check folder: installer")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
