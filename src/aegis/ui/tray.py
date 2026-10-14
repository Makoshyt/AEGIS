"""Ícone e menu na bandeja do Windows."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def create_app_icon(size: int = 64) -> QIcon:
    """Ícone desenhado em código (sem arquivos binários): quadrado arredondado com 'A'."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#3d6fd6"))
    painter.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), size * 0.22, size * 0.22)
    font = QFont("Segoe UI", int(size * 0.5))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")
    painter.end()
    return QIcon(pixmap)


class TrayController(QObject):
    toggle_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self, icon: QIcon, tooltip: str, hotkey_text: str = "", parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._menu = QMenu()
        label = "Mostrar/ocultar" + (f"\t{hotkey_text}" if hotkey_text else "")
        self.toggle_action = QAction(label, self._menu)
        self.toggle_action.triggered.connect(self.toggle_requested)
        self.quit_action = QAction("Sair", self._menu)
        self.quit_action.triggered.connect(self.quit_requested)
        self._menu.addAction(self.toggle_action)
        self._menu.addSeparator()
        self._menu.addAction(self.quit_action)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip(tooltip)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_requested.emit()
