import pytest

from aegis.core.commands import CommandRequest, InputSource
from aegis.core.dispatcher import INTERNAL_ERROR, UNKNOWN_COMMAND, Dispatcher
from aegis.skills.base import ParamSpec, ParamValidationError, Skill, SkillResult, bind_params
from aegis.skills.registry import RegistryError, SkillRegistry


class EchoSkill(Skill):
    name = "repetir"
    description = "Repete parâmetros validados."
    params = (
        ParamSpec("vezes", "quantidade", kind=int, min_value=1, max_value=3),
        ParamSpec("modo", "modo", required=False, choices=("curto", "Longo")),
    )

    def __init__(self):
        self.calls = []

    def run(self, params):
        self.calls.append(dict(params))
        return SkillResult.success("ok")


class BrokenSkill(Skill):
    name = "quebrada"
    description = "Sempre falha."

    def run(self, params):
        raise RuntimeError("detalhe interno")


class WrongReturnSkill(Skill):
    name = "errada"
    description = "Retorna tipo inválido."

    def run(self, params):
        return "texto"


@pytest.fixture
def setup():
    reg = SkillRegistry()
    echo = EchoSkill()
    for s in (echo, BrokenSkill(), WrongReturnSkill()):
        reg.register(s)
    reg.freeze()
    return Dispatcher(reg), echo


def test_requires_frozen_registry():
    with pytest.raises(RegistryError):
        Dispatcher(SkillRegistry())


def test_valid_command_runs_with_coerced_params(setup):
    dispatcher, echo = setup
    result = dispatcher.handle_text("repetir 2 LONGO")
    assert result.ok
    assert echo.calls == [{"vezes": 2, "modo": "Longo"}]


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("repetir", "Informe"),
        ("repetir dois", "inteiro"),
        ("repetir 9", "≤ 3"),
        ("repetir 0", "≥ 1"),
        ("repetir 2 medio", "Opções"),
        ("repetir 2 curto extra", "no máximo"),
        ("repetir 99999999999", "inteiro"),
    ],
)
def test_invalid_params_rejected_before_run(setup, text, fragment):
    dispatcher, echo = setup
    result = dispatcher.handle_text(text)
    assert not result.ok
    assert fragment in result.message
    assert "Uso: repetir <vezes> [modo]" in result.message
    assert echo.calls == []


def test_unknown_command(setup):
    dispatcher, _ = setup
    result = dispatcher.handle_text("formatar disco")
    assert not result.ok and result.message == UNKNOWN_COMMAND


def test_parse_error_returned_as_failure(setup):
    dispatcher, _ = setup
    assert not dispatcher.handle_text("   ").ok


def test_skill_exception_is_contained(setup, caplog):
    dispatcher, _ = setup
    result = dispatcher.handle_text("quebrada")
    assert not result.ok
    assert result.message == INTERNAL_ERROR
    assert "detalhe interno" not in result.message


def test_invalid_return_type_is_contained(setup):
    dispatcher, _ = setup
    assert dispatcher.handle_text("errada").message == INTERNAL_ERROR


def test_dispatch_accepts_voice_requests(setup):
    dispatcher, echo = setup
    req = CommandRequest("repetir", ("1",), "repetir 1", InputSource.VOICE)
    assert dispatcher.dispatch(req).ok


def test_skill_without_params_rejects_args():
    with pytest.raises(ParamValidationError, match="não aceita parâmetros"):
        bind_params([], ["; shutdown"])


def test_bind_params_max_length():
    with pytest.raises(ParamValidationError, match="excede"):
        bind_params([ParamSpec("x", "x", max_length=3)], ["abcd"])


def test_param_spec_rejects_unsupported_type():
    with pytest.raises(TypeError):
        ParamSpec("x", "x", kind=float)
