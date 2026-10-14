from types import MappingProxyType

import pytest

from aegis import __version__
from aegis.config import AllowedApp
from aegis.core.assistant import Assistant
from aegis.skills.builtin.abrir import AbrirSkill
from aegis.skills.builtin.hora import format_pt_br
from aegis.skills.builtin.status import format_uptime

from conftest import FIXED_NOW


@pytest.fixture
def assistant(config):
    launched = []
    a = Assistant(config, mode="teste", clock=lambda: FIXED_NOW, launcher=launched.append)
    a.launched = launched
    return a


def test_closed_skill_list(assistant):
    assert [s.name for s in assistant.registry.skills()] == ["abrir", "ajuda", "hora", "status"]
    assert assistant.registry.frozen


def test_hora(assistant):
    result = assistant.submit("hora")
    assert result.ok
    assert result.message == "09:05 — segunda-feira, 1 de janeiro de 2024."
    assert assistant.submit("Horário").ok
    assert assistant.submit("data").ok


def test_format_pt_br_all_months_and_days():
    from datetime import datetime

    assert "sábado" in format_pt_br(datetime(2024, 1, 6))
    assert "dezembro" in format_pt_br(datetime(2024, 12, 1))


def test_ajuda_lists_all_skills(assistant):
    result = assistant.submit("ajuda")
    assert result.ok
    for name in ("abrir <aplicativo>", "ajuda [comando]", "hora", "status"):
        assert name in result.message


def test_ajuda_details(assistant):
    result = assistant.submit("ajuda abra")
    assert result.ok
    assert "Uso: abrir <aplicativo>" in result.message
    assert not assistant.submit("ajuda inexistente").ok


def test_status(assistant):
    result = assistant.submit("status")
    assert result.ok
    assert __version__ in result.message
    assert "Python 3.12" in result.message
    assert "Habilidades: 4" in result.message
    assert "Voz: desativado" in result.message


@pytest.mark.parametrize(
    "seconds, expected", [(5, "5s"), (65, "1min 05s"), (3725, "1h 02min")]
)
def test_format_uptime(seconds, expected):
    assert format_uptime(seconds) == expected


APPS = MappingProxyType(
    {
        "bloco": AllowedApp("bloco", "Bloco de Notas", r"C:\Windows\System32\notepad.exe"),
        "calculadora": AllowedApp("calculadora", "Calculadora", r"C:\Windows\System32\calc.exe"),
    }
)


def make_abrir(exists=True, launcher=None):
    calls = []
    skill = AbrirSkill(
        APPS, launcher=launcher or calls.append, path_exists=lambda p: exists
    )
    return skill, calls


@pytest.mark.parametrize("query", ["bloco", "Bloco de Notas", "o bloco de notas", "BLOCO!"])
def test_abrir_allowed_app(query):
    skill, calls = make_abrir()
    result = skill.run({"aplicativo": query})
    assert result.ok
    assert calls == [r"C:\Windows\System32\notepad.exe"]


@pytest.mark.parametrize("query", ["cmd", "notepad", "bloco de", "calc.exe", "powershell"])
def test_abrir_rejects_unlisted(query):
    skill, calls = make_abrir()
    result = skill.run({"aplicativo": query})
    assert not result.ok
    assert "lista permitida" in result.message
    assert calls == []


def test_abrir_missing_executable():
    skill, calls = make_abrir(exists=False)
    result = skill.run({"aplicativo": "bloco"})
    assert not result.ok and "não foi encontrado" in result.message
    assert calls == []


def test_abrir_launcher_error():
    def fail(path):
        raise OSError("negado")

    skill, _ = make_abrir(launcher=fail)
    result = skill.run({"aplicativo": "calculadora"})
    assert not result.ok and "Não foi possível" in result.message


def test_abrir_without_apps():
    skill = AbrirSkill(MappingProxyType({}), launcher=lambda p: None)
    assert not skill.run({"aplicativo": "bloco"}).ok


def test_abrir_requires_param(assistant):
    result = assistant.submit("abrir")
    assert not result.ok and "Informe" in result.message
