"""Janela principal: campo de comando e histórico de respostas."""

from __future__ import annotations

import html
from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from aegis.core.commands import MAX_COMMAND_LENGTH
from aegis.skills.base import SkillResult

_STYLE = """
QMainWindow, QWidget { background: #1e2126; color: #e6e9ef;
    font-family: 'Segoe UI'; font-size: 10pt; }
QTextBrowser { background: #252930; border: 1px solid #333842; border-radius: 6px;
    padding: 8px; }
QLineEdit { background: #252930; border: 1px solid #3a404b; border-radius: 6px;
    padding: 7px 10px; }
QLineEdit:focus { border-color: #5b8def; }
QPushButton { background: #2f3540; border: 1px solid #3a404b; border-radius: 6px;
    padding: 7px 16px; }
QPushButton:hover { background: #38404c; }
QPushButton:pressed { background: #2a2f38; }
QStatusBar { color: #9aa4b2; }
"""

_COLORS = {"user": "#9aa4b2", "ok": "#e6e9ef", "error": "#e8b05c"}


class MainWindow(QMainWindow):
    def __init__(
        self,
        submit: Callable[[str], SkillResult],
        *,
        title: str = "AEGIS",
        history_limit: int = 500,
        close_to_tray: bool = True,
    ) -> None:
        super().__init__()
        self._submit = submit
        self._close_to_tray = close_to_tray
        self._allow_close = False
        self._sent: list[str] = []
        self._sent_index = 0

        self.setWindowTitle(title)
        self.resize(560, 420)
        self.setMinimumSize(380, 280)
        self.setStyleSheet(_STYLE)

        self.history = QTextBrowser()
        self.history.setOpenLinks(False)
        self.history.setOpenExternalLinks(False)
        self.history.document().setMaximumBlockCount(history_limit)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Digite um comando (ex.: ajuda)")
        self.input.setMaxLength(MAX_COMMAND_LENGTH)
        self.input.returnPressed.connect(self._on_submit)
        self.input.installEventFilter(self)

        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self._on_submit)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 8)
        layout.addWidget(self.history, 1)
        layout.addLayout(row)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._append("AEGIS", "Olá. Digite 'ajuda' para ver os comandos disponíveis.", "ok")

    # --- API pública -------------------------------------------------------------------------

    def set_status(self, message: str, *, warning: bool = False) -> None:
        color = _COLORS["error"] if warning else _COLORS["user"]
        self.statusBar().setStyleSheet(f"color: {color};")
        self.statusBar().showMessage(message)

    def show_and_focus(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def toggle_visibility(self) -> None:
        if self.isVisible() and self.isActiveWindow():
            self.hide()
        else:
            self.show_and_focus()

    def allow_close(self) -> None:
        self._allow_close = True

    def set_close_to_tray(self, enabled: bool) -> None:
        self._close_to_tray = enabled

    # --- Internos ----------------------------------------------------------------------------

    def _append(self, author: str, text: str, kind: str) -> None:
        body = html.escape(text).replace("\n", "<br>")
        self.history.append(
            f'<p style="margin:4px 0"><span style="color:{_COLORS["user"]}">'
            f"{html.escape(author)}:</span> "
            f'<span style="color:{_COLORS[kind]}">{body}</span></p>'
        )
        bar = self.history.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._sent.append(text)
        self._sent_index = len(self._sent)
        self._append("Você", text, "user")
        result = self._submit(text)
        self._append("AEGIS", result.message, "ok" if result.ok else "error")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Setas para cima/baixo navegam pelos comandos já enviados.
        if (
            watched is self.input
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
        ):
            key = event.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self._sent:
                step = -1 if key == Qt.Key.Key_Up else 1
                self._sent_index = max(0, min(len(self._sent), self._sent_index + step))
                value = self._sent[self._sent_index] if self._sent_index < len(self._sent) else ""
                self.input.setText(value)
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._close_to_tray and not self._allow_close:
            event.ignore()
            self.hide()
            return
        event.accept()
