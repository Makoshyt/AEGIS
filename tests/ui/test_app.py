import sys

import pytest
from PySide6.QtCore import Qt

from aegis.app import AegisApp, acquire_instance_lock
from aegis.core.assistant import Assistant
from aegis.ui.hotkey import GlobalHotkey

from conftest import FIXED_NOW, make_config

TEST_SEQUENCE = "Ctrl+Alt+Shift+F22"


@pytest.fixture
def app_config(tmp_path):
    return make_config(tmp_path, f"[hotkey]\nsequence = '{TEST_SEQUENCE}'\n")


def _make_app(config):
    assistant = Assistant(config, mode="janela", clock=lambda: FIXED_NOW, launcher=lambda p: None)
    return AegisApp(config, assistant=assistant)


def test_start_and_shutdown(qapp, qtbot, app_config):
    app = _make_app(app_config)
    assert app.start()
    try:
        assert app.window is not None and app.window.isVisible()
        qtbot.keyClicks(app.window.input, "hora")
        qtbot.keyClick(app.window.input, Qt.Key.Key_Return)
        assert "09:05" in app.window.history.toPlainText()
        if sys.platform == "win32":
            assert app.hotkey is not None and app.hotkey.registered
            assert TEST_SEQUENCE in app.window.statusBar().currentMessage()
    finally:
        app.shutdown()
    assert app.hotkey is None or not app.hotkey.registered
    app.shutdown()  # idempotente


def test_second_instance_is_blocked(qapp, app_config):
    first = _make_app(app_config)
    assert first.start()
    try:
        second = _make_app(app_config)
        assert second.start() is False
        assert second.window is None
    finally:
        first.shutdown()
    assert acquire_instance_lock(app_config.var_dir / "aegis.lock") is not None


@pytest.mark.skipif(sys.platform != "win32", reason="RegisterHotKey é do Windows")
def test_hotkey_conflict_keeps_app_running(qapp, app_config):
    blocker = GlobalHotkey(TEST_SEQUENCE)
    assert blocker.register()
    app = _make_app(app_config)
    try:
        assert app.start()
        assert not app.hotkey.registered
        assert "indisponível" in app.window.statusBar().currentMessage()
        assert app.assistant.submit("status").ok
    finally:
        app.shutdown()
        blocker.unregister()


def test_hotkey_disabled(qapp, tmp_path):
    config = make_config(tmp_path, "[hotkey]\nenabled = false\n")
    app = _make_app(config)
    try:
        assert app.start()
        assert app.hotkey is None
        assert "desativado" in app.window.statusBar().currentMessage()
    finally:
        app.shutdown()
