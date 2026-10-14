from aegis.ui.tray import TrayController, create_app_icon


def test_icon_is_valid(qapp):
    icon = create_app_icon()
    assert not icon.isNull()


def test_menu_actions_emit_signals(qapp, qtbot):
    tray = TrayController(create_app_icon(), "AEGIS", "Ctrl+Alt+A")
    with qtbot.waitSignal(tray.toggle_requested, timeout=1000):
        tray.toggle_action.trigger()
    with qtbot.waitSignal(tray.quit_requested, timeout=1000):
        tray.quit_action.trigger()
    assert "Ctrl+Alt+A" in tray.toggle_action.text()
