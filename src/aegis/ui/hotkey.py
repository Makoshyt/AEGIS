"""Atalho global via Win32 ``RegisterHotKey``.

Não instala hook de teclado nem exige privilégios de administrador. Se a combinação já estiver
em uso por outro programa, ``register()`` retorna ``False`` e a aplicação continua normalmente.
"""

from __future__ import annotations

import ctypes
import itertools
import logging
import sys
from ctypes import wintypes
from dataclasses import dataclass

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QCoreApplication, QObject, Signal

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
}
_ids = itertools.count(0xAE01)
_log = logging.getLogger("aegis.hotkey")

if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    _user32.RegisterHotKey.restype = wintypes.BOOL
    _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.UnregisterHotKey.restype = wintypes.BOOL
else:  # pragma: no cover - o AEGIS é voltado ao Windows
    _user32 = None


class HotkeyError(ValueError):
    pass


@dataclass(frozen=True)
class HotkeySpec:
    modifiers: int
    vk: int
    text: str


def parse_hotkey(sequence: str) -> HotkeySpec:
    """Converte 'Ctrl+Alt+A' em modificadores e virtual-key do Windows."""
    parts = [p.strip() for p in sequence.split("+")]
    if len(parts) < 2 or any(not p for p in parts):
        raise HotkeyError(f"Atalho inválido: {sequence!r}")

    modifiers = 0
    for part in parts[:-1]:
        flag = _MODIFIERS.get(part.lower())
        if flag is None:
            raise HotkeyError(f"Modificador desconhecido: {part!r}")
        if modifiers & flag:
            raise HotkeyError(f"Modificador repetido: {part!r}")
        modifiers |= flag
    if not modifiers & (MOD_CONTROL | MOD_ALT | MOD_WIN):
        raise HotkeyError("O atalho precisa incluir Ctrl, Alt ou Win.")

    key = parts[-1].upper()
    if len(key) == 1 and (key.isascii() and key.isalnum()):
        vk = ord(key)
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    else:
        raise HotkeyError(f"Tecla não suportada: {parts[-1]!r}")
    return HotkeySpec(modifiers, vk, sequence)


class _HotkeyEventFilter(QAbstractNativeEventFilter):
    def __init__(self, hotkey_id: int, callback) -> None:
        super().__init__()
        self._id = hotkey_id
        self._callback = callback

    def nativeEventFilter(self, event_type: QByteArray | bytes, message: int) -> tuple[bool, int]:
        try:
            if bytes(event_type) == b"windows_generic_MSG":
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == self._id:
                    self._callback()
                    return True, 0
        except Exception:
            _log.exception("erro ao processar evento do atalho global")
        return False, 0


class GlobalHotkey(QObject):
    activated = Signal()

    def __init__(self, sequence: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.sequence = sequence
        self.error_message = ""
        self._id = next(_ids)
        self._filter: _HotkeyEventFilter | None = None
        self._registered = False

    @property
    def registered(self) -> bool:
        return self._registered

    def register(self) -> bool:
        """Registra o atalho. Deve ser chamado na thread principal, com o QApplication criado."""
        if self._registered:
            return True
        if _user32 is None:
            self.error_message = "atalhos globais só são suportados no Windows."
            return False
        try:
            spec = parse_hotkey(self.sequence)
        except HotkeyError as exc:
            self.error_message = str(exc)
            return False

        app = QCoreApplication.instance()
        if app is None:
            self.error_message = "aplicação Qt não inicializada."
            return False

        if not _user32.RegisterHotKey(None, self._id, spec.modifiers | MOD_NOREPEAT, spec.vk):
            error = ctypes.get_last_error()
            if error == ERROR_HOTKEY_ALREADY_REGISTERED:
                self.error_message = "a combinação já está em uso por outro aplicativo."
            else:
                self.error_message = f"o Windows recusou o registro (erro {error})."
            return False

        self._filter = _HotkeyEventFilter(self._id, self.activated.emit)
        app.installNativeEventFilter(self._filter)
        self._registered = True
        _log.info("atalho global registrado: %s", self.sequence)
        return True

    def unregister(self) -> None:
        if not self._registered:
            return
        _user32.UnregisterHotKey(None, self._id)
        app = QCoreApplication.instance()
        if app is not None and self._filter is not None:
            app.removeNativeEventFilter(self._filter)
        self._filter = None
        self._registered = False
        _log.info("atalho global liberado: %s", self.sequence)
