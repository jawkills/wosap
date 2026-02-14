from __future__ import annotations

from typing import Dict, List

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.distribution_service import DistributionService


class PreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        source_dir: str,
        valid_files: List[str],
        distribution: Dict[str, List[str]],
        labels: Dict[str, str],
        remote_path: str,
        distribution_service: DistributionService,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preview")
        self.setMinimumSize(420, 360)

        layout = QVBoxLayout(self)
        title = QLabel("Ringkasan Transfer")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        preview_text = self._build_text(
            source_dir,
            valid_files,
            distribution,
            labels,
            remote_path,
            distribution_service,
        )

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(preview_text)
        layout.addWidget(text, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        ok_button.setText("Mulai")
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        cancel_button.setText("Batal")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_text(
        self,
        source_dir: str,
        valid_files: List[str],
        distribution: Dict[str, List[str]],
        labels: Dict[str, str],
        remote_path: str,
        distribution_service: DistributionService,
    ) -> str:
        total_size = distribution_service.total_size(source_dir, valid_files)
        lines = ["Ringkasan Transfer", "=" * 40, ""]
        lines.append(f"Folder: {source_dir}")
        lines.append(
            f"File: {len(valid_files)} tar.gz ({distribution_service.format_size(total_size)})"
        )
        lines.append(f"Perangkat: {len(distribution)}")
        lines.append("")
        lines.append(f"Tujuan: {remote_path}")
        lines.append("")
        lines.append("Distribusi:")
        lines.append("-" * 40)
        for index, (serial, file_list) in enumerate(distribution.items(), start=1):
            display_name = labels.get(serial, serial)
            device_size = distribution_service.total_size(source_dir, file_list)
            lines.append(f"{index}. {display_name}")
            lines.append(
                f"   {len(file_list)} file ({distribution_service.format_size(device_size)})"
            )
        lines.append("")
        lines.append("=" * 40)
        return "\n".join(lines)
