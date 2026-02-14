from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen


def build_icon(output_path: Path, size: int = 256) -> None:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)

    outer_rect = QRectF(10, 10, size - 20, size - 20)
    painter.setBrush(QColor("#f8fbff"))
    painter.setPen(QPen(QColor("#2f77d4"), 10))
    painter.drawRoundedRect(outer_rect, 56, 56)

    inner_rect = QRectF(28, 28, size - 56, size - 56)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor("#8bb7f3"), 2))
    painter.drawRoundedRect(inner_rect, 44, 44)

    painter.setPen(QPen(QColor("#1d4f90"), 2))
    font = QFont("Segoe UI", 72, QFont.Bold)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
    painter.setFont(font)
    painter.drawText(image.rect(), Qt.AlignCenter, "RST")

    painter.end()
    image.save(str(output_path))


if __name__ == "__main__":
    app = QGuiApplication([])
    out = Path(__file__).resolve().parent / "wosap.ico"
    build_icon(out)
    preview = Path(__file__).resolve().parent / "wosap.png"
    build_icon(preview)
    app.quit()
