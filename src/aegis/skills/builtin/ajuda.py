from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from aegis.skills.base import ParamSpec, Skill, SkillResult

if TYPE_CHECKING:
    from aegis.skills.registry import SkillRegistry


class AjudaSkill(Skill):
    name = "ajuda"
    description = "Lista os comandos disponíveis ou detalha um comando."
    aliases = ("help", "comandos")
    params = (ParamSpec("comando", "Comando a detalhar", required=False, max_length=32),)

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def run(self, params: Mapping[str, Any]) -> SkillResult:
        target = params.get("comando")
        if target is not None:
            skill = self._registry.resolve(target)
            if skill is None:
                return SkillResult.failure("Esse comando não existe. Digite 'ajuda' para ver a lista.")
            lines = [f"{skill.name}: {skill.description}", f"Uso: {skill.usage}"]
            if skill.aliases:
                lines.append(f"Também aceita: {', '.join(skill.aliases)}")
            return SkillResult.success("\n".join(lines))

        lines = ["Comandos disponíveis:"]
        lines += [f"• {s.usage}: {s.description}" for s in self._registry.skills()]
        lines.append("Digite 'ajuda <comando>' para mais detalhes.")
        return SkillResult.success("\n".join(lines))
