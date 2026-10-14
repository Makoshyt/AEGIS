import ctypes
import sys

import pytest

from aegis.ui.hotkey import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    WM_HOTKEY,
    GlobalHotkey,
    HotkeyError,
    parse_hotkey,
)

# Combinação incomum para não interferir no Ctrl+Alt+A de uma instância real em execução.
TEST_SEQUENCE = "Ctrl+Alt+Shift+F22"

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="RegisterHotKey é do Windows")


def test_parse_default_hotkey():
    spec = parse_hotkey("Ctrl+Alt+A")
    assert spec.modifiers == MOD_CONTROL | MOD_ALT
    assert spec.vk == ord("A")


def test_parse_function_key_and_case():
    spec = parse_hotkey("ctrl + shift + f11")
    assert spec.modifiers == MOD_CONTROL | MOD_SHIFT
    assert spec.vk == 0x7A


@pytest.mark.parametrize(
    "sequence", ["", "A", "Ctrl+", "Shift+A", "Ctrl+Ctrl+A", "Hyper+A", "Ctrl+Alt+Enter", "Ctrl+F25"]
)
def test_parse_invalid(sequence):
    with pytest.raises(HotkeyError):
        parse_hotkey(sequence)


def test_invalid_sequence_fails_gracefully(qapp):
    hk = GlobalHotkey("Shift+A")
    assert hk.register() is False
    assert "Ctrl" in hk.error_message


@windows_only
def test_register_trigger_and_unregister(qapp, qtbot):
    hk = GlobalHotkey(TEST_SEQUENCE)
    assert hk.register(), hk.error_message
    try:
        # Simula o WM_HOTKEY que o Windows enviaria à thread principal.
        thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        with qtbot.waitSignal(hk.activated, timeout=2000):
            ctypes.windll.user32.PostThreadMessageW(thread_id, WM_HOTKEY, hk._id, 0)
    finally:
        hk.unregister()
    assert not hk.registered
    hk.unregister()  # idempotente


@windows_only
def test_conflict_is_reported_without_exception(qapp):
    first = GlobalHotkey(TEST_SEQUENCE)
    second = GlobalHotkey(TEST_SEQUENCE)
    assert first.register(), first.error_message
    try:
        assert second.register() is False
        assert "em uso" in second.error_message
        assert not second.registered
    finally:
        first.unregister()
    assert second.register(), "após liberar, o atalho deve ficar disponível"
    second.unregister()
