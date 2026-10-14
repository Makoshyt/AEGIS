import pytest

from aegis.skills.base import ParamSpec, Skill, SkillResult
from aegis.skills.registry import RegistryError, SkillRegistry


def make_skill(skill_name, skill_aliases=(), skill_params=()):
    class _S(Skill):
        name = skill_name
        description = "teste"
        aliases = skill_aliases
        params = skill_params

        def run(self, params):
            return SkillResult.success("ok")

    return _S()


def test_register_and_resolve_by_name_and_alias():
    reg = SkillRegistry()
    skill = make_skill("hora", ("horário",))
    reg.register(skill)
    assert reg.resolve("hora") is skill
    assert reg.resolve("HORARIO") is skill
    assert reg.resolve("Horário!") is skill
    assert reg.resolve("outra") is None
    assert "hora" in reg and len(reg) == 1


def test_duplicate_name_or_alias_rejected():
    reg = SkillRegistry()
    reg.register(make_skill("hora", ("data",)))
    with pytest.raises(RegistryError):
        reg.register(make_skill("hora"))
    with pytest.raises(RegistryError):
        reg.register(make_skill("calendario", ("data",)))


@pytest.mark.parametrize("name", ["", "A", "Hora", "1abc", "rm -rf", "a" * 40])
def test_invalid_name_rejected(name):
    with pytest.raises(RegistryError):
        SkillRegistry().register(make_skill(name))


def test_frozen_registry_rejects_registration():
    reg = SkillRegistry()
    reg.freeze()
    with pytest.raises(RegistryError, match="congelado"):
        reg.register(make_skill("nova"))


def test_greedy_must_be_last():
    params = (ParamSpec("a", "x", greedy=True), ParamSpec("b", "y"))
    with pytest.raises(RegistryError, match="greedy"):
        SkillRegistry().register(make_skill("teste", skill_params=params))


def test_only_skill_instances():
    with pytest.raises(TypeError):
        SkillRegistry().register(object())  # type: ignore[arg-type]


def test_skills_sorted():
    reg = SkillRegistry()
    reg.register(make_skill("zeta"))
    reg.register(make_skill("alfa"))
    assert [s.name for s in reg.skills()] == ["alfa", "zeta"]
