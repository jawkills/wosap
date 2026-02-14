from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class ProgressPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.label = QLabel("Progres:")
        self.percent_label = QLabel("0%")
        self.percent_label.setProperty("accent", True)
        top_row.addWidget(self.label)
        top_row.addStretch()
        top_row.addWidget(self.percent_label)
        layout.addLayout(top_row)

        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 100)
        self.total_progress.setValue(0)
        self.total_progress.setTextVisible(False)
        layout.addWidget(self.total_progress)

        self.summary = QLabel("0/0 file")
        self.summary.setProperty("muted", True)
        layout.addWidget(self.summary)

    def set_progress(self, percent: float, completed: int, total: int) -> None:
        safe = max(0.0, min(100.0, percent))
        self.total_progress.setValue(int(safe))
        self.percent_label.setText(f"{int(safe)}%")
        self.summary.setText(f"{completed}/{total} file")

    def reset(self) -> None:
        self.set_progress(0.0, 0, 0)
