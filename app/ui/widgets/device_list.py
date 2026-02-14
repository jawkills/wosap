from __future__ import annotations

from typing import Callable, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.state import DeviceState


STATUS_MARKER = {
    "idle": ("●", "#8d99a9"),
    "running": ("○", "#3a8dde"),
    "success": ("✓", "#1d9449"),
    "error": ("✗", "#c72d2d"),
}


class DeviceListWidget(QWidget):
    def __init__(
        self,
        on_select_changed: Callable[[str, bool], None],
        on_label_changed: Callable[[str, str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_select_changed = on_select_changed
        self.on_label_changed = on_label_changed
        self._device_rows: Dict[str, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setMinimumHeight(220)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 6, 6, 6)
        self.container_layout.setSpacing(6)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

    def set_devices(self, devices: list[DeviceState]) -> None:
        self._clear_rows()
        for index, device in enumerate(devices, start=1):
            self._add_device_row(index, device)

        if not devices:
            label = QLabel("Tidak ada perangkat")
            label.setProperty("muted", True)
            self.container_layout.insertWidget(0, label)

    def update_device(self, device: DeviceState) -> None:
        row = self._device_rows.get(device.serial)
        if not row:
            return
        row["checkbox"].setChecked(device.selected)
        row["progress"].setValue(int(device.progress))
        marker, color = STATUS_MARKER.get(device.status, STATUS_MARKER["idle"])
        row["status"].setText(marker)
        row["status"].setStyleSheet(f"color: {color};")

    def set_all_selected(self, selected: bool) -> None:
        for serial, row in self._device_rows.items():
            row["checkbox"].blockSignals(True)
            row["checkbox"].setChecked(selected)
            row["checkbox"].blockSignals(False)
            self.on_select_changed(serial, selected)

    def _add_device_row(self, index: int, device: DeviceState) -> None:
        card = QFrame()
        card.setObjectName("deviceCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)

        top_row = QHBoxLayout()
        checkbox = QCheckBox()
        checkbox.setChecked(device.selected)
        checkbox.stateChanged.connect(
            lambda state, serial=device.serial: self.on_select_changed(
                serial, state == Qt.CheckState.Checked.value
            )
        )
        top_row.addWidget(checkbox)

        name_input = QLineEdit(device.label or f"HP-{index}")
        name_input.setMinimumWidth(104)
        name_input.editingFinished.connect(
            lambda serial=device.serial, field=name_input: self.on_label_changed(
                serial, field.text().strip()
            )
        )
        top_row.addWidget(name_input)

        serial_label = QLabel(device.serial[:8])
        serial_label.setProperty("muted", True)
        top_row.addWidget(serial_label)

        top_row.addStretch()
        status = QLabel("●")
        status.setProperty("status", True)
        top_row.addWidget(status)
        card_layout.addLayout(top_row)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(device.progress))
        progress.setTextVisible(False)
        card_layout.addWidget(progress)

        self.container_layout.insertWidget(self.container_layout.count() - 1, card)
        self._device_rows[device.serial] = {
            "widget": card,
            "checkbox": checkbox,
            "name": name_input,
            "status": status,
            "progress": progress,
        }
        self.update_device(device)

    def _clear_rows(self) -> None:
        self._device_rows.clear()
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
