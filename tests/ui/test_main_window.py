import pytest
from PySide6.QtCore import Qt

from aegis.skills.base import SkillResult
from aegis.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot):
    received = []

    def submit(text):
        received.append(text)
        if text == "html":
            return SkillResult.failure("<b>negrito</b> & <script>x</script>")
        return SkillResult.success(f"resposta para {text}")

    w = MainWindow(submit, history_limit=50)
    qtbot.addWidget(w)
    w.received = received
    w.show()
    return w


def test_submit_with_enter_updates_history(window, qtbot):
    qtbot.keyClicks(window.input, "hora")
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert window.received == ["hora"]
    text = window.history.toPlainText()
    assert "Você: hora" in text
    assert "AEGIS: resposta para hora" in text
    assert window.input.text() == ""


def test_submit_with_button(window, qtbot):
    window.input.setText("status")
    qtbot.mouseClick(window.send_button, Qt.MouseButton.LeftButton)
    assert window.received == ["status"]


def test_empty_input_ignored(window, qtbot):
    window.input.setText("   ")
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert window.received == []


def test_responses_are_escaped(window, qtbot):
    window.input.setText("html")
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert "<b>negrito</b> & <script>x</script>" in window.history.toPlainText()


def test_history_navigation_with_arrows(window, qtbot):
    for cmd in ("um", "dois"):
        window.input.setText(cmd)
        qtbot.keyClick(window.input, Qt.Key.Key_Return)
    qtbot.keyClick(window.input, Qt.Key.Key_Up)
    assert window.input.text() == "dois"
    qtbot.keyClick(window.input, Qt.Key.Key_Up)
    assert window.input.text() == "um"
    qtbot.keyClick(window.input, Qt.Key.Key_Down)
    qtbot.keyClick(window.input, Qt.Key.Key_Down)
    assert window.input.text() == ""


def test_history_limit(window, qtbot):
    for i in range(80):
        window.input.setText(f"c{i}")
        qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert window.history.document().blockCount() <= 50


def test_close_hides_to_tray(window):
    window.close()
    assert not window.isVisible()
    window.show_and_focus()
    assert window.isVisible()


def test_close_without_tray_accepts(qtbot):
    w = MainWindow(lambda t: SkillResult.success(""), close_to_tray=False)
    qtbot.addWidget(w)
    w.show()
    assert w.close() is True


def test_toggle_visibility(window):
    window.hide()
    window.toggle_visibility()
    assert window.isVisible()


def test_status_message(window):
    window.set_status("Atalho indisponível", warning=True)
    assert window.statusBar().currentMessage() == "Atalho indisponível"
