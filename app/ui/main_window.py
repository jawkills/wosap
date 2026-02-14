from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.state import AppState, DeviceState
from app.services.adb_service import AdbService
from app.services.distribution_service import DistributionService
from app.services.settings_service import SettingsService
from app.ui.widgets.device_list import DeviceListWidget
from app.ui.widgets.preview_dialog import PreviewDialog
from app.workers.transfer_worker import TransferWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wosap")
        self.resize(470, 760)
        self.setAcceptDrops(True)

        self.state = AppState()
        self.settings = SettingsService()
        self.distribution_service = DistributionService(
            self.settings.default_destination_base
        )
        self.adb_service = AdbService()

        self.thread_pool = QThreadPool.globalInstance()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.completed_lock = threading.Lock()
        self.active_workers = 0
        self.failed_devices: dict[str, str] = {}

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_devices)

        self.device_labels = self.settings.load_device_labels()

        self._build_ui()
        self._connect_state_signals()
        self._load_settings()
        self.refresh_devices()
        self.start_auto_refresh()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        header = QLabel("Wosap")
        header.setObjectName("headerTitle")
        root_layout.addWidget(header)

        root_layout.addWidget(self._build_source_card())
        root_layout.addWidget(self._build_devices_card(), 3)
        root_layout.addWidget(self._build_log_card(), 1)
        root_layout.addWidget(self._build_control_row())

    def _build_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)
        return frame, layout

    def _build_source_card(self) -> QFrame:
        frame, layout = self._build_card("Source & Tujuan")

        path_row = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Pilih folder sumber…")
        self.source_input.textChanged.connect(self._on_source_changed)
        path_row.addWidget(self.source_input, 1)

        browse_btn = QPushButton("Pilih")
        browse_btn.clicked.connect(self.browse_folder)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        self.file_count_label = QLabel("File: 0")
        self.file_count_label.setProperty("muted", True)
        layout.addWidget(self.file_count_label)

        destination_row = QHBoxLayout()
        destination_label = QLabel("Tujuan (base):")
        destination_label.setProperty("muted", True)
        destination_row.addWidget(destination_label)

        self.destination_input = QLineEdit()
        self.destination_input.editingFinished.connect(self._on_destination_commit)
        destination_row.addWidget(self.destination_input, 1)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_destination_base)
        destination_row.addWidget(reset_btn)
        layout.addLayout(destination_row)

        self.destination_hint = QLabel("")
        self.destination_hint.setProperty("muted", True)
        layout.addWidget(self.destination_hint)

        mode_row = QHBoxLayout()
        self.auto_mode = QRadioButton("Auto tanggal (YYYYMMDD)")
        self.manual_mode = QRadioButton("Path manual penuh")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.auto_mode)
        self.mode_group.addButton(self.manual_mode)
        self.auto_mode.clicked.connect(self._on_destination_mode_changed)
        self.manual_mode.clicked.connect(self._on_destination_mode_changed)
        mode_row.addWidget(self.auto_mode)
        mode_row.addWidget(self.manual_mode)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        return frame

    def _build_devices_card(self) -> QFrame:
        frame, layout = self._build_card("Perangkat")

        header_row = QHBoxLayout()
        self.devices_count = QLabel("Perangkat (0)")
        header_row.addWidget(self.devices_count)
        header_row.addStretch()

        interval_label = QLabel("Refresh:")
        interval_label.setProperty("muted", True)
        header_row.addWidget(interval_label)

        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(10, 300)
        self.refresh_interval.setValue(30)
        self.refresh_interval.valueChanged.connect(lambda _: self.start_auto_refresh())
        header_row.addWidget(self.refresh_interval)
        layout.addLayout(header_row)

        self.device_list = DeviceListWidget(
            self._on_device_selected, self._on_label_changed
        )
        layout.addWidget(self.device_list, 1)

        control_row = QHBoxLayout()
        select_all = QPushButton("Pilih Semua")
        select_all.clicked.connect(lambda: self.device_list.set_all_selected(True))
        control_row.addWidget(select_all)

        clear_all = QPushButton("Hapus Semua")
        clear_all.setProperty("danger", True)
        clear_all.clicked.connect(lambda: self.device_list.set_all_selected(False))
        control_row.addWidget(clear_all)
        layout.addLayout(control_row)

        return frame

    def _build_log_card(self) -> QFrame:
        frame, layout = self._build_card("Log")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(84)
        layout.addWidget(self.log_area)
        return frame

    def _build_control_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.show_transfer_preview)
        row.addWidget(self.preview_btn)

        self.start_btn = QPushButton("Mulai")
        self.start_btn.setProperty("success", True)
        self.start_btn.clicked.connect(self.start_transfer)
        row.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Jeda")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        row.addWidget(self.pause_btn)

        return container

    def _connect_state_signals(self) -> None:
        self.state.devices_changed.connect(self._render_devices)
        self.state.run_state_changed.connect(self._on_run_state_changed)
        self.state.log_added.connect(self._append_log)

    def _load_settings(self) -> None:
        destination_base, destination_mode = self.settings.load_app_settings()
        destination_base, warning = self.distribution_service.sanitize_destination_base(
            destination_base
        )
        self.state.destination_base = destination_base
        self.state.destination_mode = destination_mode
        self.destination_input.setText(destination_base)
        if destination_mode == "manual":
            self.manual_mode.setChecked(True)
        else:
            self.auto_mode.setChecked(True)
        self._update_destination_hint()
        if warning:
            self.state.log(warning)

    def start_auto_refresh(self) -> None:
        self.auto_refresh_timer.stop()
        self.auto_refresh_timer.start(self.refresh_interval.value() * 1000)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        local_path = urls[0].toLocalFile()
        if local_path and Path(local_path).is_dir():
            self.source_input.setText(local_path)
        else:
            QMessageBox.warning(self, "Peringatan", "Tolong drop folder, bukan file.")

    def browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pilih folder sumber")
        if folder:
            self.source_input.setText(folder)

    def _on_source_changed(self, text: str) -> None:
        self.state.source_dir = text.strip()
        self._refresh_file_count()

    def _refresh_file_count(self) -> None:
        src = self.state.source_dir
        if src and Path(src).exists():
            try:
                files = self.distribution_service.get_sorted_files(src)
                self.file_count_label.setProperty("muted", True)
                self.file_count_label.setText(f"File: {len(files)}")
                self.file_count_label.style().polish(self.file_count_label)
                return
            except Exception:
                pass
        self.file_count_label.setText("Folder tidak valid")
        self.file_count_label.setStyleSheet("color: #c72d2d;")

    def _on_destination_commit(self) -> None:
        destination_base, warning = self.distribution_service.sanitize_destination_base(
            self.destination_input.text()
        )
        self.state.destination_base = destination_base
        self.destination_input.setText(destination_base)
        self.settings.save_app_settings(destination_base, self.state.destination_mode)
        self._update_destination_hint()
        if warning:
            self.state.log(warning)

    def _reset_destination_base(self) -> None:
        self.destination_input.setText(self.settings.default_destination_base)
        self._on_destination_commit()

    def _on_destination_mode_changed(self) -> None:
        self.state.destination_mode = (
            "manual" if self.manual_mode.isChecked() else "auto_date"
        )
        self.settings.save_app_settings(
            self.state.destination_base, self.state.destination_mode
        )
        self._update_destination_hint()

    def _build_remote_path(self, notify_warning: bool = False) -> str:
        remote_path, warning = self.distribution_service.build_remote_path(
            self.state.destination_base,
            self.state.destination_mode,
        )
        if warning and notify_warning:
            self.state.log(warning)
        return remote_path

    def _update_destination_hint(self) -> None:
        if self.state.destination_mode == "manual":
            hint = f"Mode manual aktif: {self.state.destination_base}"
        else:
            hint = f"Mode auto aktif (YYYYMMDD): {self._build_remote_path()}"
        self.destination_hint.setText(hint)

    def refresh_devices(self) -> None:
        if self.state.is_running:
            return
        try:
            current = self.state.devices
            devices = []
            for index, serial in enumerate(self.adb_service.list_devices(), start=1):
                previous = current.get(serial)
                label = self.device_labels.get(serial, f"HP-{index}")
                devices.append(
                    DeviceState(
                        serial=serial,
                        label=label,
                        selected=previous.selected if previous else True,
                        progress=0.0,
                        status="idle",
                    )
                )
            self.state.set_devices(devices)
            self.state.log(f"Ditemukan {len(devices)} perangkat")
        except Exception as exc:
            QMessageBox.critical(
                self, "Error ADB", "Tidak bisa menjalankan ADB. Cek PATH."
            )
            self.state.log(f"Error: {exc}")

    def _render_devices(self) -> None:
        devices = list(self.state.devices.values())
        self.devices_count.setText(f"Perangkat ({len(devices)})")
        self.device_list.set_devices(devices)

    def _on_device_selected(self, serial: str, selected: bool) -> None:
        device = self.state.devices.get(serial)
        if not device:
            return
        device.selected = selected

    def _on_label_changed(self, serial: str, label: str) -> None:
        clean = label or serial
        self.device_labels[serial] = clean
        if serial in self.state.devices:
            self.state.devices[serial].label = clean
        self.settings.save_device_labels(self.device_labels)

    def _selected_devices(self) -> list[str]:
        return [serial for serial, item in self.state.devices.items() if item.selected]

    def _validate_transfer_request(self) -> tuple[str, list[str], list[str]] | None:
        src = self.state.source_dir
        if not src or not Path(src).exists():
            QMessageBox.warning(self, "Peringatan", "Pilih folder sumber yang valid.")
            return None

        selected = self._selected_devices()
        if not selected:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal satu perangkat.")
            return None

        files = self.distribution_service.get_sorted_files(src)
        valid_files, errors = self.distribution_service.validate_files(src, files)
        for error in errors:
            self.state.log(f"  ✗ {error}")
        if not valid_files:
            QMessageBox.warning(
                self, "Peringatan", "Tidak ada file valid untuk transfer."
            )
            return None

        return src, selected, valid_files

    def show_transfer_preview(self) -> None:
        request = self._validate_transfer_request()
        if not request:
            return
        src, selected_devices, valid_files = request
        distribution = self.distribution_service.calculate_distribution(
            valid_files, selected_devices
        )
        remote_path = self._build_remote_path()

        dialog = PreviewDialog(
            self,
            src,
            valid_files,
            distribution,
            self.device_labels,
            remote_path,
            self.distribution_service,
        )
        if dialog.exec() == dialog.Accepted:
            self.start_transfer()

    def start_transfer(self) -> None:
        if self.state.is_running:
            return
        request = self._validate_transfer_request()
        if not request:
            return

        src, selected_devices, valid_files = request
        distribution = self.distribution_service.calculate_distribution(
            valid_files, selected_devices
        )
        remote_path = self._build_remote_path(notify_warning=True)

        self.state.set_run_state(True, False)
        self.pause_event.set()
        self.failed_devices = {}
        self.active_workers = 0
        self.state.set_total(len(valid_files))
        self.state.log(
            f"Mendistribusikan {len(valid_files)} file ke {len(selected_devices)} perangkat..."
        )
        self.state.log(f"Tujuan otomatis: {remote_path}")

        for serial, files in distribution.items():
            if not files:
                continue
            self.active_workers += 1
            self.state.update_device_progress(serial, 0.0)
            self.state.update_device_status(serial, "running")

            worker = TransferWorker(
                serial=serial,
                src_dir=src,
                files=files,
                remote_path=remote_path,
                pause_event=self.pause_event,
                adb_service=self.adb_service,
            )
            worker.signals.progress.connect(self._on_worker_progress)
            worker.signals.file_completed.connect(self._on_worker_file_completed)
            worker.signals.rename_notice.connect(self._on_worker_rename_notice)
            worker.signals.completed.connect(self._on_worker_completed)
            worker.signals.failed.connect(self._on_worker_failed)
            self.thread_pool.start(worker)

        if self.active_workers == 0:
            self._finish_transfer()

    def toggle_pause(self) -> None:
        if not self.state.is_running:
            return
        if self.state.is_paused:
            self.pause_event.set()
            self.state.set_run_state(True, False)
            self.state.log("Dilanjutkan")
        else:
            self.pause_event.clear()
            self.state.set_run_state(True, True)
            self.state.log("Dijeda")

    def _on_worker_progress(self, serial: str, progress: float) -> None:
        self.state.update_device_progress(serial, progress)

    def _on_worker_file_completed(self, _serial: str) -> None:
        with self.completed_lock:
            self.state.increment_completed(1)

    def _on_worker_rename_notice(
        self, serial: str, old_name: str, new_name: str
    ) -> None:
        label = self.device_labels.get(serial, serial)
        self.state.log(
            f"! {label}: nama duplikat {old_name}, disalin sebagai {new_name}"
        )

    def _on_worker_completed(self, serial: str, file_count: int) -> None:
        self.state.update_device_status(serial, "success")
        label = self.device_labels.get(serial, serial)
        self.state.log(f"✓ {label}: {file_count} file")
        self.active_workers -= 1
        if self.active_workers <= 0:
            self._finish_transfer()

    def _on_worker_failed(self, serial: str, message: str) -> None:
        self.state.update_device_status(serial, "error", message)
        label = self.device_labels.get(serial, serial)
        self.state.log(f"✗ {label}: {message}")
        self.failed_devices[serial] = message
        self.active_workers -= 1
        if self.active_workers <= 0:
            self._finish_transfer()

    def _finish_transfer(self) -> None:
        success_count = len(
            [
                d
                for d in self.state.devices.values()
                if d.selected and d.status == "success"
            ]
        )
        failed_count = len(self.failed_devices)
        self.state.log("✓ Distribusi selesai!")

        if failed_count:
            failed_lines = [
                f"- {self.device_labels.get(serial, serial)}: {message}"
                for serial, message in self.failed_devices.items()
            ]
            detail = "\n".join(failed_lines)
            QMessageBox.warning(
                self,
                "Distribusi selesai (dengan error)",
                f"Sukses: {success_count}\nGagal: {failed_count}\n\n{detail}",
            )
        else:
            QMessageBox.information(self, "Sukses", "Distribusi berhasil!")

        self.state.set_run_state(False, False)
        for device in self.state.devices.values():
            device.progress = 0.0
            if device.status not in {"error", "success"}:
                device.status = "idle"
        self.state.devices_changed.emit()

    def _on_run_state_changed(self, is_running: bool, is_paused: bool) -> None:
        self.start_btn.setEnabled(not is_running)
        self.preview_btn.setEnabled(not is_running)
        self.pause_btn.setEnabled(is_running)
        if is_running and is_paused:
            self.pause_btn.setText("Lanjut")
        elif is_running:
            self.pause_btn.setText("Jeda")
        else:
            self.pause_btn.setText("Jeda")

    def _append_log(self, line: str) -> None:
        self.log_area.append(line)
