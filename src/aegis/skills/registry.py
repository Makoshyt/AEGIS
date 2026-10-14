"""Registro fechado de habilidades.

As habilidades são registradas explicitamente no código (sem descoberta dinâmica de plugins).
Depois de ``freeze()``, nenhuma habilidade pode ser adicionada.
"""

from __future__ import annotations

import re

from aegis.core.commands import normalize_token
from aegis.skills.base import Skill

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


class RegistryError(RuntimeError):
    pass


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._index: dict[str, str] = {}
        self._frozen = False

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        self._frozen = True

    def register(self, skill: Skill) -> None:
        if self._frozen:
            raise RegistryError("O registro de habilidades está congelado.")
        if not isinstance(skill, Skill):
            raise TypeError("Somente instâncias de Skill podem ser registradas.")
        if not _NAME_RE.match(skill.name):
            raise RegistryError(f"Nome de habilidade inválido: {skill.name!r}")
        if any(spec.greedy for spec in skill.params[:-1]):
            raise RegistryError(f"{skill.name}: apenas o último parâmetro pode ser 'greedy'.")

        keys = {normalize_token(k) for k in (skill.name, *skill.aliases)}
        if "" in keys:
            raise RegistryError(f"{skill.name}: alias vazio.")
        clashes = keys & self._index.keys()
        if clashes:
            raise RegistryError(f"{skill.name}: nome/alias já registrado: {', '.join(sorted(clashes))}")

        self._skills[skill.name] = skill
        for key in keys:
            self._index[key] = skill.name

    def resolve(self, keyword: str) -> Skill | None:
        name = self._index.get(normalize_token(keyword))
        return self._skills[name] if name else None

    def skills(self) -> tuple[Skill, ...]:
        return tuple(self._skills[name] for name in sorted(self._skills))

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: object) -> bool:
        return name in self._skills
