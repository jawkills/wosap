from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import List


class AdbService:
    def list_devices(self) -> List[str]:
        output = subprocess.check_output(["adb", "devices"], text=True)
        lines = output.strip().splitlines()[1:]
        return [line.split("\t")[0] for line in lines if "\tdevice" in line]

    def ensure_remote_dir(self, serial: str, remote_path: str) -> None:
        subprocess.run(
            ["adb", "-s", serial, "shell", f"mkdir -p {shlex.quote(remote_path)}"],
            check=True,
            capture_output=True,
        )

    def push_folder(self, serial: str, local_dir: Path, remote_path: str) -> None:
        subprocess.run(
            [
                "adb",
                "-s",
                serial,
                "push",
                f"{local_dir.as_posix()}/.",
                f"{remote_path}/",
            ],
            check=True,
            capture_output=True,
        )
