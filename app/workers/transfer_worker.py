from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, QRunnable, Signal

from app.services.adb_service import AdbService


class TransferWorkerSignals(QObject):
    status = Signal(str, str)
    progress = Signal(str, float)
    file_completed = Signal(str)
    rename_notice = Signal(str, str, str)
    completed = Signal(str, int)
    failed = Signal(str, str)


class TransferWorker(QRunnable):
    def __init__(
        self,
        serial: str,
        src_dir: str,
        files: List[str],
        remote_path: str,
        pause_event,
        adb_service: AdbService,
    ) -> None:
        super().__init__()
        self.serial = serial
        self.src_dir = Path(src_dir)
        self.files = files
        self.remote_path = remote_path
        self.pause_event = pause_event
        self.adb_service = adb_service
        self.signals = TransferWorkerSignals()
        self.setAutoDelete(True)

    def _wait_if_paused(self) -> None:
        while not self.pause_event.is_set():
            time.sleep(0.2)

    def _unique_name(self, target_name: str, used_names: set[str]) -> str:
        if target_name not in used_names:
            return target_name
        if target_name.lower().endswith(".tar.gz"):
            base_name = target_name[:-7]
            ext = ".tar.gz"
        else:
            base_name = Path(target_name).stem
            ext = Path(target_name).suffix

        counter = 2
        candidate = f"{base_name}_{counter}{ext}"
        while candidate in used_names:
            counter += 1
            candidate = f"{base_name}_{counter}{ext}"
        return candidate

    def run(self) -> None:
        temp_dir_path: Path | None = None
        try:
            self.signals.status.emit(self.serial, "running")
            self.adb_service.ensure_remote_dir(self.serial, self.remote_path)

            temp_dir_path = Path(tempfile.mkdtemp(prefix=f"wosap_{self.serial}_"))
            used_names: set[str] = set()

            for index, rel_path in enumerate(self.files):
                self._wait_if_paused()
                src_file = self.src_dir / rel_path
                target_name = src_file.name
                unique_name = self._unique_name(target_name, used_names)
                if unique_name != target_name:
                    self.signals.rename_notice.emit(
                        self.serial, target_name, unique_name
                    )

                used_names.add(unique_name)
                shutil.copy2(src_file, temp_dir_path / unique_name)

                progress = ((index + 1) / len(self.files)) * 100
                self.signals.progress.emit(self.serial, progress)
                self.signals.file_completed.emit(self.serial)

            self._wait_if_paused()
            self.adb_service.push_folder(self.serial, temp_dir_path, self.remote_path)
            self.signals.status.emit(self.serial, "success")
            self.signals.completed.emit(self.serial, len(self.files))
        except Exception as exc:
            self.signals.status.emit(self.serial, "error")
            self.signals.failed.emit(self.serial, str(exc))
        finally:
            if temp_dir_path and temp_dir_path.exists():
                shutil.rmtree(temp_dir_path, ignore_errors=True)
