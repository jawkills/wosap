from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import QObject, Signal


@dataclass
class DeviceState:
    serial: str
    label: str
    selected: bool = True
    progress: float = 0.0
    status: str = "idle"
    message: str = ""


class AppState(QObject):
    devices_changed = Signal()
    progress_changed = Signal(float, int, int)
    run_state_changed = Signal(bool, bool)
    log_added = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.source_dir: str = ""
        self.destination_base: str = "//sdcard/XPersonal"
        self.destination_mode: str = "auto_date"
        self.is_running: bool = False
        self.is_paused: bool = False
        self.total_completed: int = 0
        self.total_files: int = 0
        self.devices: Dict[str, DeviceState] = {}

    def set_devices(self, devices: List[DeviceState]) -> None:
        self.devices = {device.serial: device for device in devices}
        self.devices_changed.emit()

    def set_run_state(self, is_running: bool, is_paused: bool = False) -> None:
        self.is_running = is_running
        self.is_paused = is_paused
        self.run_state_changed.emit(is_running, is_paused)

    def update_device_status(self, serial: str, status: str, message: str = "") -> None:
        device = self.devices.get(serial)
        if not device:
            return
        device.status = status
        device.message = message
        self.devices_changed.emit()

    def update_device_progress(self, serial: str, progress: float) -> None:
        device = self.devices.get(serial)
        if not device:
            return
        device.progress = max(0.0, min(100.0, progress))
        self.devices_changed.emit()

    def set_total(self, total_files: int) -> None:
        self.total_completed = 0
        self.total_files = max(0, total_files)
        self.progress_changed.emit(0.0, self.total_completed, self.total_files)

    def increment_completed(self, count: int = 1) -> None:
        self.total_completed += count
        total_pct = 0.0
        if self.total_files > 0:
            total_pct = (self.total_completed / self.total_files) * 100.0
        self.progress_changed.emit(total_pct, self.total_completed, self.total_files)

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_added.emit(f"[{timestamp}] {message}")
