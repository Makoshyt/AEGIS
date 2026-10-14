"""Composição da aplicação desktop: núcleo, janela, bandeja e atalho global.

Inicialização em etapas (``start``) e encerramento idempotente em ordem inversa (``shutdown``).
"""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from aegis import __version__
from aegis.config import AegisConfig
from aegis.core.assistant import Assistant
from aegis.ui.hotkey import GlobalHotkey
from aegis.ui.main_window import MainWindow
from aegis.ui.tray import TrayController, create_app_icon

EXIT_ALREADY_RUNNING = 1
_log = logging.getLogger("aegis.app")


def acquire_instance_lock(path: Path) -> QLockFile | None:
    """Retorna o lock adquirido ou ``None`` se outra instância já estiver em execução."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(path))
    # 0 = o lock só é considerado obsoleto se o processo dono não existir mais.
    lock.setStaleLockTime(0)
    return lock if lock.tryLock(100) else None


class AegisApp:
    def __init__(self, config: AegisConfig, *, assistant: Assistant | None = None) -> None:
        self.config = config
        self.assistant = assistant
        self.qt_app: QApplication | None = None
        self.window: MainWindow | None = None
        self.tray: TrayController | None = None
        self.hotkey: GlobalHotkey | None = None
        self._lock: QLockFile | None = None
        self._signal_timer: QTimer | None = None
        self._started = False
        self._stopped = False

    @property
    def lock_path(self) -> Path:
        return self.config.var_dir / "aegis.lock"

    def start(self) -> bool:
        """Monta a aplicação. Retorna ``False`` se já houver outra instância."""
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setApplicationName(self.config.general.name)
        self.qt_app.setApplicationVersion(__version__)

        self._lock = acquire_instance_lock(self.lock_path)
        if self._lock is None:
            _log.warning("outra instância do AEGIS já está em execução")
            return False

        if self.assistant is None:
            self.assistant = Assistant(self.config, mode="janela")

        icon = create_app_icon()
        self.qt_app.setWindowIcon(icon)
        tray_available = TrayController.available()

        self.window = MainWindow(
            self.assistant.submit,
            title=self.config.general.name,
            history_limit=self.config.ui.history_limit,
            close_to_tray=self.config.ui.close_to_tray and tray_available,
        )

        if tray_available:
            self.tray = TrayController(icon, self.config.general.name, self.config.hotkey.sequence)
            self.tray.toggle_requested.connect(self.window.toggle_visibility)
            self.tray.quit_requested.connect(self.qt_app.quit)
            self.tray.show()
            self.qt_app.setQuitOnLastWindowClosed(False)
        else:
            _log.warning("bandeja do sistema indisponível; fechar a janela encerrará o AEGIS")
            self.qt_app.setQuitOnLastWindowClosed(True)

        self._setup_hotkey()

        if not (self.config.ui.start_hidden and tray_available):
            self.window.show_and_focus()

        self.qt_app.aboutToQuit.connect(self.shutdown)
        self._started = True
        _log.info("interface iniciada (bandeja=%s)", tray_available)
        return True

    def _setup_hotkey(self) -> None:
        assert self.window is not None
        sequence = self.config.hotkey.sequence
        if not self.config.hotkey.enabled:
            self.window.set_status("Atalho global desativado na configuração.")
            return
        self.hotkey = GlobalHotkey(sequence)
        if self.hotkey.register():
            self.hotkey.activated.connect(self.window.toggle_visibility)
            self.window.set_status(f"Pronto. Atalho: {sequence}")
        else:
            message = f"Atalho {sequence} indisponível: {self.hotkey.error_message}"
            _log.warning(message)
            self.window.set_status(message, warning=True)

    def _install_sigint_handler(self) -> None:
        # Permite encerrar com Ctrl+C quando iniciado pelo terminal.
        assert self.qt_app is not None
        signal.signal(signal.SIGINT, lambda *_: self.qt_app.quit())
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(lambda: None)
        self._signal_timer.start(500)

    def run(self) -> int:
        if not self.start():
            assert self.qt_app is not None
            QMessageBox.information(
                None, self.config.general.name, "O AEGIS já está em execução (veja a bandeja)."
            )
            return EXIT_ALREADY_RUNNING
        self._install_sigint_handler()
        assert self.qt_app is not None
        code = self.qt_app.exec()
        self.shutdown()
        return code

    def shutdown(self) -> None:
        """Libera recursos em ordem inversa. Pode ser chamada várias vezes."""
        if self._stopped:
            return
        self._stopped = True
        if self._signal_timer is not None:
            self._signal_timer.stop()
        if self.hotkey is not None:
            self.hotkey.unregister()
        if self.tray is not None:
            self.tray.hide()
        if self.window is not None:
            self.window.allow_close()
            self.window.close()
        if self._lock is not None:
            self._lock.unlock()
        if self._started:
            _log.info("interface encerrada")
